from typing import Protocol

from pydantic import ValidationError

from api.agent.retrieval import Retriever
from api.agent.types import AgentError, AgentRun, Message, Passage, ToolCall, ToolSpec
from api.engines.protocols import Document
from api.planning.schema import PlanDraft, PlanMeta, ProductionPlan, Retrieval, Voice

RETRIEVE = "retrieve"
SUBMIT = "submit_lesson"


class ToolCallingLLM(Protocol):
    async def next_action(self, messages: list[Message], tools: list[ToolSpec]) -> ToolCall: ...


SYSTEM_PROMPT = (
    "You are Sikto's microlearning agent. Turn the provided source into ONE focused "
    "microlearning lesson. You may call the retrieve tool to pull relevant passages from "
    "the indexed source before deciding. When you have enough context, call submit_lesson "
    "exactly once with: a lesson (title, summary, difficulty of intro/intermediate/advanced, "
    "3-5 key_points, 2-3 quiz items each with question/answer/explanation and optional choices) "
    "and an ordered list of segments (id, order, narration, caption, and visual_type from "
    "title/bullet/talking-point/equation/diagram/code). Ground the key points and summary in the "
    "retrieved source passages (each is tagged with its [source <id>]); prefer claims the sources "
    "support. Always finish by calling submit_lesson."
)

RETRIEVE_TOOL = ToolSpec(
    name=RETRIEVE,
    description="Search the indexed source material for passages relevant to a query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "k": {"type": "integer", "description": "How many passages to return."},
        },
        "required": ["query"],
    },
)

SUBMIT_TOOL = ToolSpec(
    name=SUBMIT,
    description="Submit the finished microlearning lesson once you have enough context.",
    parameters=PlanDraft.model_json_schema(),
)


class MicrolearningAgent:
    """A tool-using agent that grounds itself via retrieval and emits a ProductionPlan."""

    def __init__(
        self,
        llm: ToolCallingLLM,
        retriever: Retriever,
        *,
        voice: Voice,
        retrieval: Retrieval,
        planner_model: str,
        embedding_model: str,
        tts_model: str,
        engine_version: str,
        max_steps: int = 6,
        retrieve_k: int = 4,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._voice = voice
        self._retrieval = retrieval
        self._planner_model = planner_model
        self._embedding_model = embedding_model
        self._tts_model = tts_model
        self._engine_version = engine_version
        self._max_steps = max_steps
        self._retrieve_k = retrieve_k

    async def run(self, document: Document, source_ids: list[str]) -> AgentRun:
        messages = [Message("system", SYSTEM_PROMPT), Message("user", _source_prompt(document))]
        tools = [RETRIEVE_TOOL, SUBMIT_TOOL]
        trace: list[ToolCall] = []
        retrieved: list[Passage] = []

        for _ in range(self._max_steps):
            call = await self._llm.next_action(messages, tools)
            trace.append(call)

            if call.name == SUBMIT:
                try:
                    draft = PlanDraft.model_validate(call.arguments)
                except ValidationError as exc:
                    messages.append(
                        Message(
                            "user",
                            f"submit_lesson was invalid: {exc}. Fix the issues and call "
                            "submit_lesson again.",
                        )
                    )
                    continue
                return AgentRun(
                    plan=self._assemble(draft, source_ids),
                    trace=trace,
                    retrieved=retrieved,
                )

            if call.name == RETRIEVE:
                query = str(call.arguments.get("query", "")).strip()
                k = int(call.arguments.get("k") or self._retrieve_k)
                passages = await self._retriever.retrieve(query, k) if query else []
                retrieved.extend(passages)
                messages.append(Message("user", _retrieval_result(query, passages)))
                continue

            messages.append(
                Message("user", f"Unknown tool {call.name!r}; use retrieve or submit_lesson.")
            )

        raise AgentError("agent did not submit a valid lesson within the step budget")

    def _assemble(self, draft: PlanDraft, source_ids: list[str]) -> ProductionPlan:
        return ProductionPlan(
            lesson=draft.lesson,
            segments=draft.segments,
            voice=self._voice,
            retrieval=self._retrieval,
            meta=PlanMeta(
                source_ids=source_ids,
                planner_model=self._planner_model,
                embedding_model=self._embedding_model,
                tts_model=self._tts_model,
                engine_version=self._engine_version,
            ),
        )


class AgentPlanner:
    """Adapts the MicrolearningAgent to the Planner interface (yields just the plan)."""

    def __init__(self, agent: MicrolearningAgent) -> None:
        self._agent = agent

    async def plan(self, document: Document, source_ids: list[str]) -> ProductionPlan:
        run = await self._agent.run(document, source_ids)
        return run.plan


def _source_prompt(document: Document) -> str:
    title = document.title or "(untitled)"
    return f"Source title: {title}\n\nSource content:\n{document.text}"


def _retrieval_result(query: str, passages: list[Passage]) -> str:
    if not passages:
        return f"retrieve({query!r}) returned no passages."
    joined = "\n---\n".join(f"[source {p.source_id}] {p.content}" for p in passages)
    return f"retrieve({query!r}) returned:\n{joined}"
