import Fastify, { type FastifyInstance } from 'fastify';
import type { SceneAudio, SceneDocument } from './remotion/schema.ts';
import { RemotionRunner } from './sandbox/remotion-runner.ts';
import { RemotionSceneRenderer, type SceneRenderer } from './sandbox/scene-runner.ts';
import type { Renderer } from './sandbox/types.ts';

export function build(
  runner: Renderer = new RemotionRunner(),
  sceneRenderer: SceneRenderer = new RemotionSceneRenderer(),
): FastifyInstance {
  const app = Fastify({ bodyLimit: 32 * 1024 * 1024 });

  app.get('/health', async () => ({ status: 'ok' }));

  app.post('/render', async () => ({ video_ref: 'renders/stub-lesson.mp4' }));

  // Render a declarative SceneDocument to an mp4.
  app.post('/render-scene', async (request, reply) => {
    const body = request.body as {
      document?: SceneDocument;
      audio?: SceneAudio[];
      manim_clips?: Record<string, string>;
    };
    if (!body.document) {
      reply.code(400);
      return { error: 'document is required' };
    }
    try {
      const result = await sceneRenderer.render(body.document, {
        audio: body.audio,
        manimClips: body.manim_clips,
      });
      return { video_b64: result.video.toString('base64') };
    } catch (err) {
      reply.code(500);
      return { error: (err as Error).message };
    }
  });

  // Render an AI-generated Remotion composition (legacy code-gen path).
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
  const port = Number(process.env.RENDER_PORT ?? process.env.PORT ?? 8001);

  // Graceful shutdown — ensures the port is released when turbo / Ctrl-C kills
  // the process, preventing "port already in use" on the next restart.
  const shutdown = () => {
    app.close().then(() => process.exit(0), () => process.exit(1));
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  app
    .listen({ port })
    .then(() => console.log(`render service listening on http://localhost:${port}`))
    .catch((err: NodeJS.ErrnoException) => {
      // Fastify's logger is off by default, so surface the reason explicitly.
      if (err.code === 'EADDRINUSE') {
        console.error(
          `render: port ${port} is already in use — another render process is ` +
            `running. Stop it (e.g. \`lsof -tiTCP:${port} | xargs kill\`) or set RENDER_PORT.`,
        );
      } else {
        console.error('render: failed to start —', err);
      }
      process.exit(1);
    });
}
