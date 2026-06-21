'use client';

import { Maximize, Minimize, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react';
import { cn } from '@/lib/utils';

function fmt(s: number): string {
  if (!Number.isFinite(s)) return '0:00';
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
}

// A small, professional MP4 player themed to the pixel/lime look: a thin
// timeline, controls that fade in on hover, and a vertical volume slider that
// only appears when you hover the speaker.
export function VideoPlayer({ src }: { src: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const idle = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [active, setActive] = useState(true); // controls visible
  const [showVolume, setShowVolume] = useState(false);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
  }, []);

  const wake = useCallback(() => {
    setActive(true);
    if (idle.current) clearTimeout(idle.current);
    idle.current = setTimeout(() => setActive(false), 2200);
  }, []);

  // Keyboard shortcuts when the player has focus.
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const v = videoRef.current;
      if (!v) return;
      if (e.key === ' ' || e.key === 'k') {
        e.preventDefault();
        togglePlay();
      } else if (e.key === 'ArrowRight') v.currentTime = Math.min(v.duration, v.currentTime + 5);
      else if (e.key === 'ArrowLeft') v.currentTime = Math.max(0, v.currentTime - 5);
      else if (e.key === 'm') setMuted((m) => !m);
      else if (e.key === 'f') void toggleFullscreen();
      wake();
    },
    [togglePlay, wake],
  );

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onTime = () => setCurrent(v.currentTime);
    const onMeta = () => setDuration(v.duration);
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onVol = () => {
      setVolume(v.volume);
      setMuted(v.muted);
    };
    v.addEventListener('timeupdate', onTime);
    v.addEventListener('loadedmetadata', onMeta);
    v.addEventListener('play', onPlay);
    v.addEventListener('pause', onPause);
    v.addEventListener('volumechange', onVol);
    return () => {
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('loadedmetadata', onMeta);
      v.removeEventListener('play', onPlay);
      v.removeEventListener('pause', onPause);
      v.removeEventListener('volumechange', onVol);
    };
  }, []);

  useEffect(() => {
    const v = videoRef.current;
    if (v) v.muted = muted;
  }, [muted]);
  useEffect(() => {
    const v = videoRef.current;
    if (v) v.volume = volume;
  }, [volume]);

  useEffect(() => {
    const onFs = () => setFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  async function toggleFullscreen() {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) await document.exitFullscreen();
    else await el.requestFullscreen().catch(() => {});
  }

  const seekTo = useCallback((clientX: number, track: HTMLDivElement) => {
    const v = videoRef.current;
    if (!v || !Number.isFinite(v.duration)) return;
    const rect = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    v.currentTime = ratio * v.duration;
    setCurrent(v.currentTime);
  }, []);

  const onSeekPointer = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      const track = e.currentTarget;
      track.setPointerCapture(e.pointerId);
      seekTo(e.clientX, track);
      const move = (ev: PointerEvent) => seekTo(ev.clientX, track);
      const up = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
    },
    [seekTo],
  );

  const setVol = useCallback((clientY: number, track: HTMLDivElement) => {
    const rect = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, 1 - (clientY - rect.top) / rect.height));
    setVolume(ratio);
    setMuted(ratio === 0);
  }, []);

  const onVolPointer = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      const track = e.currentTarget;
      track.setPointerCapture(e.pointerId);
      setVol(e.clientY, track);
      const move = (ev: PointerEvent) => setVol(ev.clientY, track);
      const up = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
    },
    [setVol],
  );

  const progress = duration > 0 ? (current / duration) * 100 : 0;
  const volPct = (muted ? 0 : volume) * 100;
  const controlsVisible = active || !playing;

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onPointerMove={wake}
      onMouseLeave={() => playing && setActive(false)}
      className="group relative w-full overflow-hidden border-2 border-border bg-black shadow-pixel-sm outline-none"
      style={{ aspectRatio: '16 / 9' }}
    >
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        ref={videoRef}
        src={src}
        playsInline
        onClick={togglePlay}
        className="h-full w-full"
      />

      {/* center play affordance when paused */}
      {!playing ? (
        <button
          type="button"
          onClick={togglePlay}
          aria-label="Play"
          className="absolute inset-0 flex items-center justify-center bg-black/25 transition-colors hover:bg-black/35"
        >
          <span className="flex size-16 items-center justify-center border-2 border-border bg-primary text-primary-foreground shadow-pixel">
            <Play className="size-7" />
          </span>
        </button>
      ) : null}

      {/* control bar */}
      <div
        className={cn(
          'absolute inset-x-0 bottom-0 flex flex-col gap-1.5 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-3 pb-2 pt-8 transition-opacity duration-200',
          controlsVisible ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      >
        {/* timeline */}
        <div
          role="slider"
          aria-label="Seek"
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(current)}
          tabIndex={0}
          onPointerDown={onSeekPointer}
          className="group/seek relative flex h-3 cursor-pointer items-center"
        >
          <div className="relative h-1 w-full rounded-full bg-white/25">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-primary"
              style={{ width: `${progress}%` }}
            />
            <div
              className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 scale-0 rounded-full border border-border bg-primary transition-transform group-hover/seek:scale-100"
              style={{ left: `${progress}%` }}
            />
          </div>
        </div>

        {/* buttons row */}
        <div className="flex items-center gap-2 text-foreground">
          <button type="button" onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} className={iconBtn}>
            {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
          </button>

          {/* volume: speaker + vertical slider on hover */}
          <div
            className="relative flex items-center"
            onMouseEnter={() => setShowVolume(true)}
            onMouseLeave={() => setShowVolume(false)}
          >
            <button type="button" onClick={() => setMuted((m) => !m)} aria-label={muted ? 'Unmute' : 'Mute'} className={iconBtn}>
              {muted || volume === 0 ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
            </button>
            {showVolume ? (
              <div className="absolute bottom-full left-1/2 mb-2 -translate-x-1/2 border-2 border-border bg-surface p-2 shadow-pixel-sm">
                <div
                  onPointerDown={onVolPointer}
                  className="relative h-20 w-1.5 cursor-pointer rounded-full bg-white/25"
                >
                  <div
                    className="absolute inset-x-0 bottom-0 rounded-full bg-primary"
                    style={{ height: `${volPct}%` }}
                  />
                  <div
                    className="absolute left-1/2 size-3 -translate-x-1/2 translate-y-1/2 rounded-full border border-border bg-primary"
                    style={{ bottom: `${volPct}%` }}
                  />
                </div>
              </div>
            ) : null}
          </div>

          <span className="font-pixel text-xs tabular-nums text-white/90">
            {fmt(current)} / {fmt(duration)}
          </span>

          <button type="button" onClick={toggleFullscreen} aria-label="Fullscreen" className={cn(iconBtn, 'ml-auto')}>
            {fullscreen ? <Minimize className="size-4" /> : <Maximize className="size-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}

const iconBtn =
  'flex size-8 items-center justify-center text-white/90 transition-colors hover:text-primary';
