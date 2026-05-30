import { ToolLoopAgent, jsonSchema, stepCountIs, tool } from 'ai';

function buildAgent() {
  const model = process.env.AGENT_MODEL;

  if (!model) {
    throw new Error(
      'AGENT_MODEL is not set. Set it in apps/web/.env.local, e.g. AGENT_MODEL="anthropic/claude-sonnet-4-5", and provide AI_GATEWAY_API_KEY.',
    );
  }

  return new ToolLoopAgent({
    model,
    instructions:
      'You are Sikto, a concise and helpful assistant for a video automation and microlearning platform.',
    stopWhen: stepCountIs(10),
    tools: {
      getCurrentTime: tool({
        description: 'Get the current server time as an ISO-8601 string.',
        inputSchema: jsonSchema<{ timezone?: string }>({
          type: 'object',
          properties: {
            timezone: {
              type: 'string',
              description: 'IANA timezone name, e.g. "America/New_York". Defaults to UTC.',
            },
          },
        }),
        execute: async ({ timezone }) => {
          return { iso: new Date().toISOString(), timezone: timezone ?? 'UTC' };
        },
      }),
    },
  });
}

let agent: ReturnType<typeof buildAgent> | undefined;

export function getSiktoAgent() {
  agent ??= buildAgent();
  return agent;
}
