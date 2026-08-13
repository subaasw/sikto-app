'use client';

import { Player, type PlayerRef } from '@remotion/player';
import { MarketingScene } from '@sikto/motion-kit';
import { FPS, type Scene } from '@sikto/scene-kit';
import { useEffect, useRef } from 'react';

/**
 * Motion scenes in the live player: the same MarketingScene the MP4 uses,
 * inside a PAUSED @remotion/player that we seek from the lesson clock every
 * tick. Seek-driven (not play-driven) so it can never drift from the
 * narration audio, and scrubbing works for free.
 */
export function MotionScenePlayer({
  scene,
  progressMs,
  durationMs,
}: {
  scene: Scene;
  progressMs: number;
  durationMs: number;
}) {
  const ref = useRef<PlayerRef>(null);
  const durationInFrames = Math.max(1, Math.round((durationMs / 1000) * FPS));
  useEffect(() => {
    ref.current?.seekTo(Math.min(durationInFrames - 1, Math.max(0, Math.round((progressMs / 1000) * FPS))));
  }, [progressMs, durationInFrames]);
  return (
    <Player
      ref={ref}
      component={MarketingScene}
      inputProps={{ scene, durationMs }}
      durationInFrames={durationInFrames}
      compositionWidth={1280}
      compositionHeight={720}
      fps={FPS}
      controls={false}
      clickToPlay={false}
      acknowledgeRemotionLicense
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
    />
  );
}
