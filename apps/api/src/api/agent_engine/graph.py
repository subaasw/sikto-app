"""Assemble the brain as a LangGraph state machine and expose a simple entrypoint.

    research ─▶ outline ─▶ compose ─▶ critique ─▶ vision_qa ──(issues?)──▶ repair ─▶ ...
                                                       │                      │
                                                       └────────(clean)───────┴──▶ END
"""

from typing import Any, cast

from langgraph.graph import END, StateGraph

from api.agent_engine.llm import BrainError, StructuredLLM, structured_llm_from_settings
from api.agent_engine.nodes import BrainNodes
from api.agent_engine.research import WebSearch, web_search_from_settings
from api.agent_engine.state import BrainState
from api.agent_engine.vision import VisionReviewer, vision_reviewer_from_settings
from api.scenes.assemble import divide_scenes
from api.scenes.contrast import ensure_legible
from api.scenes.schema import SceneDocument
from api.scenes.templates import Template, get_template


def build_brain(nodes: BrainNodes) -> Any:
    graph = StateGraph(BrainState)
    graph.add_node("research", nodes.research)
    graph.add_node("outline", nodes.outline)
    graph.add_node("compose", nodes.compose)
    graph.add_node("critique", nodes.critique)
    graph.add_node("vision_qa", nodes.vision_qa)
    graph.add_node("repair", nodes.repair)
    graph.set_entry_point("research")
    graph.add_edge("research", "outline")
    graph.add_edge("outline", "compose")
    # compose → critique (editor) → vision_qa (renders + inspects) → route → repair.
    # critique and vision_qa each add quality/visual issues once; repair fixes them.
    graph.add_edge("compose", "critique")
    graph.add_edge("critique", "vision_qa")
    graph.add_conditional_edges("vision_qa", nodes.route, {"repair": "repair", "done": END})
    graph.add_conditional_edges("repair", nodes.route, {"repair": "repair", "done": END})
    return graph.compile()


class AgentBrain:
    """Pipeline-facing wrapper around the brain graph (the SceneBrain interface)."""

    def __init__(
        self,
        llm: StructuredLLM | None = None,
        *,
        search: WebSearch | None = None,
        max_repairs: int = 2,
    ) -> None:
        self._llm = llm
        self._search = search if search is not None else web_search_from_settings()
        self._max_repairs = max_repairs

    async def generate(
        self,
        source_text: str,
        source_title: str,
        template: Template | None = None,
        mode: str = "auto",
    ) -> SceneDocument:
        return await generate_scene_document(
            source_text,
            source_title=source_title,
            llm=self._llm,
            search=self._search,
            max_repairs=self._max_repairs,
            template=template,
            mode=mode,
        )


async def generate_scene_document(
    source_text: str,
    *,
    source_title: str = "",
    llm: StructuredLLM | None = None,
    search: WebSearch | None = None,
    vision: VisionReviewer | None = None,
    max_repairs: int = 2,
    template: Template | None = None,
    mode: str = "auto",
) -> SceneDocument:
    tmpl = template or get_template(None)
    nodes = BrainNodes(
        llm or structured_llm_from_settings(),
        search=search,
        vision=vision or vision_reviewer_from_settings(),
        max_repairs=max_repairs,
        style=tmpl.style,
        theme=tmpl.theme,
        mode=mode,
    )
    brain = build_brain(nodes)
    initial: BrainState = {
        "source_title": source_title,
        "source_text": source_text,
        "research": "",
        "outline": None,
        "document": None,
        "issues": [],
        "repairs": 0,
    }
    final = await brain.ainvoke(initial)
    document = final["document"]
    if document is None:
        raise BrainError("brain produced no scene document")
    document = cast(SceneDocument, document)
    # Legibility gate: whatever the director painted, text must read (repairs,
    # never rejects — a lesson always renders).
    ensure_legible(document.theme)
    # Director pass: split any over-crowded scene into sequential scenes. Runs
    # after repair so it never interferes with the validate/repair loop.
    return document.model_copy(update={"scenes": divide_scenes(document.scenes)})
