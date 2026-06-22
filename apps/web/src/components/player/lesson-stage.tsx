'use client';

import {
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { Captions, SceneStage } from '@sikto/scene-kit';
import type { SceneAudioTrack } from '@/lib/api';
import { ASPECT_RATIO_CSS, sceneDurationMs, type Scene, type SceneDocument } from '@/lib/scene/types';
import { cn } from '@/lib/utils';

/** Cumulative start time (ms) of each scene, plus the total. */
function offsetsFrom(durations: number[]): { offsets: number[]; total: number } {
  const offsets: number[] = [];
  let acc = 0;
  for (const d of durations) {
    offsets.push(acc);
    acc += d;
  }
  return { offsets, total: acc };
}

function locate(offsets: number[], total: number, ms: number): { index: number; localMs: number } {
  let index = 0;
  for (let i = 0; i < offsets.length; i++) {
    if (ms >= offsets[i]) index = i;
  }
  return { index, localMs: Math.min(ms - offsets[index], total - offsets[index]) };
}

function fmt(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// Rough spoken-duration estimate (~165 wpm) so live narration fits its scene.
function estimateNarrationMs(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2500, Math.round((words / 165) * 60_000));
}

// How many reveal steps a scene has (one per animated element; min 1).
function stepsOf(scene: Scene): number {
  return Math.max(1, scene.animations.length);
}

const speechSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

export function LessonStage({
  document,
  audio = [],
}: {
  document: SceneDocument;
  audio?: SceneAudioTrack[];
}) {
  const audioMap = useMemo(
    () => Object.fromEntries(audio.map((a) => [a.scene_id, a])) as Record<string, SceneAudioTrack>,
    [audio],
  );
  const hasNarration = audio.length > 0;

  // Each scene lasts as long as its narration so the visuals and voice-over stay
  // in lock-step: the pre-rendered audio duration when present, otherwise an
  // estimate of how long the narration takes to speak (for live text-to-voice).
  const durations = useMemo(
    () =>
      document.scenes.map((s) => {
        const track = audioMap[s.id];
        const narration = s.narration?.text?.trim();
        const raw = track
          ? track.duration_ms
          : narration
            ? estimateNarrationMs(narration)
            : sceneDurationMs(s);
        // Never let a missing/NaN duration poison the timeline (→ NaN playhead).
        return Number.isFinite(raw) && raw > 0 ? Math.max(1, raw) : 4000;
      }),
    [document, audioMap],
  );
  const { offsets, total } = useMemo(() => offsetsFrom(durations), [durations]);

  // Short title per scene (its heading) for the chapter strip.
  const sceneTitles = useMemo(
    () =>
      document.scenes.map(
        (s, i) => s.elements.find((e) => e.type === 'heading')?.text?.trim() || `Scene ${i + 1}`,
      ),
    [document],
  );

  const [playheadMs, setPlayheadMs] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [syncToken, setSyncToken] = useState(0);
  // Class/step-through mode: teacher advances reveals one click at a time.
  const [classMode, setClassMode] = useState(false);
  const [pos, setPos] = useState({ scene: 0, reveal: 1 });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const timeline = locate(offsets, total, playheadMs);
  const activeIndex = classMode ? pos.scene : timeline.index;
  const scene = document.scenes[activeIndex];
  const localMs = timeline.localMs;
  const currentAudioUrl = audioMap[scene.id]?.url ?? '';
  const currentWords = audioMap[scene.id]?.words ?? [];

  // ---- timeline playback (disabled while in class mode) --------------------
  // When the current scene has narration audio, the AUDIO element is the master
  // clock: the playhead (and so the visuals + captions) follow the real voice
  // position, so they can't drift ahead of it. Scenes without audio fall back to
  // a wall-clock advance.
  useEffect(() => {
    if (!playing || classMode) return;
    let raf = 0;
    let last: number | undefined;
    const tick = (ts: number) => {
      const dt = last === undefined ? 0 : ts - last;
      last = ts;
      setPlayheadMs((prev) => {
        const { index } = locate(offsets, total, prev);
        const track = audioMap[document.scenes[index]?.id];
        const el = audioRef.current;
        let next: number;
        if (track && el && el.src && !el.paused && el.readyState >= 2 && Number.isFinite(el.currentTime)) {
          const audioMs = Math.min(el.currentTime * 1000, track.duration_ms);
          // Audio finished but more scenes remain → roll onto the next scene.
          next =
            audioMs >= track.duration_ms - 60 && index < document.scenes.length - 1
              ? offsets[index + 1] + 1
              : offsets[index] + audioMs;
        } else {
          next = prev + dt;
        }
        if (next >= total) {
          setPlaying(false);
          return total;
        }
        return next;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, classMode, offsets, total, audioMap, document.scenes]);

  // Load the current scene's narration and align it to the playhead (timeline mode).
  useEffect(() => {
    if (classMode) return;
    const el = audioRef.current;
    if (!el) return;
    if (!currentAudioUrl) {
      el.removeAttribute('src');
      return;
    }
    if (el.src !== currentAudioUrl) el.src = currentAudioUrl;
    const target = localMs / 1000;
    if (Math.abs(el.currentTime - target) > 0.35) el.currentTime = target;
    if (playing) void el.play().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAudioUrl, activeIndex, syncToken, classMode]);

  // Mirror the play/pause state onto the audio element (timeline mode).
  useEffect(() => {
    if (classMode) return;
    const el = audioRef.current;
    if (!el || !currentAudioUrl) return;
    if (playing) void el.play().catch(() => {});
    else el.pause();
  }, [playing, currentAudioUrl, classMode]);

  // Live text-to-voice (timeline mode): browser speech reads the current scene.
  useEffect(() => {
    if (classMode || hasNarration || !speechSupported) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const text = scene.narration?.text?.trim();
    if (playing && !muted && text) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.97;
      synth.speak(utterance);
    }
    return () => synth.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasNarration, playing, muted, activeIndex, syncToken, classMode]);

  // Class mode owns audio: speak each scene's narration once, from the start,
  // when the teacher moves to it.
  useEffect(() => {
    if (!classMode) return;
    const el = audioRef.current;
    const url = audioMap[scene.id]?.url;
    if (el && url) {
      el.src = url;
      el.currentTime = 0;
      if (!muted) void el.play().catch(() => {});
      else el.pause();
    }
    if (!hasNarration && speechSupported) {
      const synth = window.speechSynthesis;
      synth.cancel();
      const text = scene.narration?.text?.trim();
      if (!muted && text) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.97;
        synth.speak(utterance);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classMode, pos.scene, muted]);

  const toggle = useCallback(() => {
    if (!playing && playheadMs >= total) {
      setPlayheadMs(0);
      setSyncToken((t) => t + 1);
    }
    setPlaying((p) => !p);
  }, [playing, playheadMs, total]);

  const goTo = useCallback(
    (sceneIdx: number) => {
      const clamped = Math.max(0, Math.min(document.scenes.length - 1, sceneIdx));
      setPlayheadMs(offsets[clamped]);
      setSyncToken((t) => t + 1);
    },
    [document.scenes.length, offsets],
  );

  const seek = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const ratio = (event.clientX - rect.left) / rect.width;
      setPlayheadMs(Math.max(0, Math.min(total, ratio * total)));
      setSyncToken((t) => t + 1);
    },
    [total],
  );

  const enterClassMode = useCallback(() => {
    setPlaying(false);
    if (speechSupported) window.speechSynthesis.cancel();
    setPos({ scene: timeline.index, reveal: 1 });
    setClassMode(true);
  }, [timeline.index]);

  const exitClassMode = useCallback(() => {
    if (speechSupported) window.speechSynthesis.cancel();
    audioRef.current?.pause();
    setPlayheadMs(offsets[pos.scene] ?? 0);
    setSyncToken((t) => t + 1);
    setClassMode(false);
  }, [offsets, pos.scene]);

  // Advance/retreat one reveal step, rolling across scene boundaries.
  const step = useCallback(
    (delta: 1 | -1) => {
      setPos((prev) => {
        const scenes = document.scenes;
        const steps = stepsOf(scenes[prev.scene]);
        if (delta === 1) {
          if (prev.reveal < steps) return { ...prev, reveal: prev.reveal + 1 };
          if (prev.scene < scenes.length - 1) return { scene: prev.scene + 1, reveal: 1 };
          return prev;
        }
        if (prev.reveal > 1) return { ...prev, reveal: prev.reveal - 1 };
        if (prev.scene > 0) {
          const ps = prev.scene - 1;
          return { scene: ps, reveal: stepsOf(scenes[ps]) };
        }
        return prev;
      });
    },
    [document.scenes],
  );

  // Keyboard control for class mode (space / arrows).
  useEffect(() => {
    if (!classMode) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === ' ' || e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault();
        step(1);
      } else if (e.key === 'ArrowLeft' || e.key === 'Backspace') {
        e.preventDefault();
        step(-1);
      } else if (e.key === 'Escape') {
        exitClassMode();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [classMode, step, exitClassMode]);

  const totalSteps = stepsOf(scene);

  return (
    <div className="flex flex-col gap-3">
      <div
        className="relative w-full overflow-hidden border-2 border-border"
        style={{
          aspectRatio: ASPECT_RATIO_CSS[document.aspect_ratio],
          containerType: 'inline-size',
          background: document.theme.background,
        }}
      >
        {/* Hard cut between scenes (no crossfade) — matches the MP4. */}
        <div key={scene.id} className="absolute inset-0">
          <SceneStage
            scene={scene}
            theme={document.theme}
            progressMs={localMs}
            sceneDurationMs={durations[activeIndex]}
            revealCount={classMode ? pos.reveal : undefined}
            words={currentWords}
            profile={document.profile}
          />
        </div>

        {classMode ? (
          // Click anywhere on the stage to reveal the next step.
          <button
            type="button"
            onClick={() => step(1)}
            aria-label="Next step"
            className="absolute inset-0 cursor-pointer bg-transparent"
          />
        ) : !playing ? (
          <button
            type="button"
            onClick={toggle}
            aria-label="Play"
            className="absolute inset-0 flex items-center justify-center bg-black/30 transition-colors hover:bg-black/40"
          >
            <span className="flex size-16 items-center justify-center border-2 border-border bg-primary text-primary-foreground shadow-pixel">
              {playheadMs >= total ? <RotateCcw className="size-7" /> : <Play className="size-7" />}
            </span>
          </button>
        ) : null}

        {currentWords.length ? (
          <Captions words={currentWords} progressMs={localMs} theme={document.theme} />
        ) : scene.narration.caption ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-linear-to-t from-black/70 to-transparent px-[4%] pb-[3%] pt-[8%] text-center">
            <span className="text-[2.4cqw] text-white">{scene.narration.caption}</span>
          </div>
        ) : null}

        {/* Per-scene narration; hidden, driven by the player clock. */}
        <audio ref={audioRef} muted={muted} preload="auto" className="hidden" />
      </div>

      {classMode ? (
        <ClassControls
          sceneIndex={pos.scene}
          sceneCount={document.scenes.length}
          reveal={pos.reveal}
          totalSteps={totalSteps}
          muted={muted}
          showMute={hasNarration || speechSupported}
          onPrev={() => step(-1)}
          onNext={() => step(1)}
          onMute={() => setMuted((m) => !m)}
          onExit={exitClassMode}
        />
      ) : (
        <>
          {/* progress */}
          <div
            className="h-2 w-full cursor-pointer border-2 border-border bg-muted"
            onClick={seek}
            role="slider"
            aria-label="Seek"
            aria-valuenow={Math.round((playheadMs / total) * 100)}
            tabIndex={0}
          >
            <div className="h-full bg-primary" style={{ width: `${(playheadMs / total) * 100}%` }} />
          </div>

          {/* controls */}
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => goTo(activeIndex - 1)} aria-label="Previous scene" className={ctrl}>
              <SkipBack className="size-4" />
            </button>
            <button type="button" onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} className={cn(ctrl, 'bg-primary text-primary-foreground')}>
              {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
            </button>
            <button type="button" onClick={() => goTo(activeIndex + 1)} aria-label="Next scene" className={ctrl}>
              <SkipForward className="size-4" />
            </button>

            {hasNarration || speechSupported ? (
              <button
                type="button"
                onClick={() => setMuted((m) => !m)}
                aria-label={muted ? 'Unmute' : 'Mute'}
                title={hasNarration ? 'Narration' : 'Live text-to-speech'}
                className={ctrl}
              >
                {muted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
              </button>
            ) : null}

            <span className="font-pixel text-xs text-muted-foreground">
              {fmt(playheadMs)} / {fmt(total)}
            </span>

            <button
              type="button"
              onClick={enterClassMode}
              title="Step through the lesson one reveal at a time"
              className={cn(ctrl, 'ml-auto w-auto gap-2 px-3 font-pixel text-xs uppercase tracking-wide')}
            >
              <GraduationCap className="size-4" /> Class mode
            </button>
          </div>

          {document.scenes.length > 1 ? (
            <ChapterStrip titles={sceneTitles} activeIndex={activeIndex} onSelect={goTo} />
          ) : null}
        </>
      )}
    </div>
  );
}

function ChapterStrip({
  titles,
  activeIndex,
  onSelect,
}: {
  titles: string[];
  activeIndex: number;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {titles.map((title, i) => {
        const active = i === activeIndex;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(i)}
            title={title}
            className={cn(
              'flex max-w-44 shrink-0 items-center gap-2 border-2 border-border px-2.5 py-1.5 text-left text-xs transition-colors',
              active ? 'bg-primary text-primary-foreground' : 'bg-surface text-foreground hover:bg-muted',
            )}
          >
            <span className="font-pixel">{String(i + 1).padStart(2, '0')}</span>
            <span className="truncate">{title}</span>
          </button>
        );
      })}
    </div>
  );
}

function ClassControls({
  sceneIndex,
  sceneCount,
  reveal,
  totalSteps,
  muted,
  showMute,
  onPrev,
  onNext,
  onMute,
  onExit,
}: {
  sceneIndex: number;
  sceneCount: number;
  reveal: number;
  totalSteps: number;
  muted: boolean;
  showMute: boolean;
  onPrev: () => void;
  onNext: () => void;
  onMute: () => void;
  onExit: () => void;
}) {
  const atStart = sceneIndex === 0 && reveal === 1;
  const atEnd = sceneIndex === sceneCount - 1 && reveal === totalSteps;
  return (
    <div className="flex items-center gap-3">
      <button type="button" onClick={onPrev} aria-label="Previous step" disabled={atStart} className={cn(ctrl, atStart && 'opacity-40')}>
        <ChevronLeft className="size-4" />
      </button>
      <button type="button" onClick={onNext} aria-label="Next step" disabled={atEnd} className={cn(ctrl, 'bg-primary text-primary-foreground', atEnd && 'opacity-40')}>
        <ChevronRight className="size-4" />
      </button>

      {showMute ? (
        <button type="button" onClick={onMute} aria-label={muted ? 'Unmute' : 'Mute'} className={ctrl}>
          {muted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
        </button>
      ) : null}

      <span className="font-pixel text-xs uppercase tracking-wide text-muted-foreground">
        Scene {sceneIndex + 1}/{sceneCount} · Step {reveal}/{totalSteps}
      </span>
      <span className="ml-auto hidden font-pixel text-[10px] uppercase tracking-wide text-muted-foreground sm:inline">
        Space / → next · ← back · Esc exit
      </span>
      <button type="button" onClick={onExit} aria-label="Exit class mode" className={cn(ctrl, 'gap-2')}>
        <X className="size-4" />
      </button>
    </div>
  );
}

const ctrl =
  'flex size-9 items-center justify-center border-2 border-border bg-surface text-foreground transition-colors hover:bg-muted';
