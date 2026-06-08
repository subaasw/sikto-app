import Fastify, { type FastifyInstance } from 'fastify';
import { RemotionRunner } from './sandbox/remotion-runner.ts';
import type { Renderer } from './sandbox/types.ts';

export function build(runner: Renderer = new RemotionRunner()): FastifyInstance {
  const app = Fastify();

  app.get('/health', async () => ({ status: 'ok' }));

  app.post('/render', async () => ({ video_ref: 'renders/stub-lesson.mp4' }));

  app.post('/render-code', async (request, reply) => {
    const { code, composition } = request.body as { code?: string; composition?: string };
    if (!code) {
      reply.code(400);
      return { error: 'code is required' };
    }
    try {
      const result = await runner.run(code, composition ?? 'MainComposition');
      return { video_b64: result.video.toString('base64') };
    } catch (err) {
      reply.code(500);
      return { error: (err as Error).message };
    }
  });

  return app;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const app = build();
  app.listen({ port: 8001 }).catch((err) => {
    app.log.error(err);
    process.exit(1);
  });
}
