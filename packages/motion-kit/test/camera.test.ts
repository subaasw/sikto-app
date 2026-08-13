import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cameraAt, ZOOM_MAX } from '../src/camera';
import { wobbleAt, WOBBLE_FPS } from '../src/wobble';

test('camera stays clamped and overscanned for the whole scene', () => {
  const cam = { drift: 'right', zoom: 'in', tilt_deg: 5 } as const; // tilt beyond clamp
  for (let t = 0; t <= 10000; t += 250) {
    const p = cameraAt(t, 10000, cam);
    assert.ok(p.scale >= 1.02 && p.scale <= ZOOM_MAX, `scale ${p.scale} at ${t}`);
    assert.ok(Math.abs(p.rot) <= 2, `rot ${p.rot} at ${t}`);
  }
  // drift actually moves the camera, ending right of where it started
  assert.ok(cameraAt(10000, 10000, cam).x > cameraAt(0, 10000, cam).x);
});

test('camera is deterministic and holds at the end', () => {
  const cam = { drift: 'up', zoom: 'out', tilt_deg: -1 } as const;
  assert.deepEqual(cameraAt(4000, 8000, cam), cameraAt(4000, 8000, cam));
  // past the end it clamps (no runaway motion on padded scenes)
  assert.deepEqual(cameraAt(9000, 8000, cam), cameraAt(8000, 8000, cam));
});

test('wobble steps at WOBBLE_FPS, is subtle, seeded, deterministic', () => {
  const stepMs = 1000 / WOBBLE_FPS;
  const a = wobbleAt(10, 's1');
  assert.deepEqual(a, wobbleAt(stepMs - 1, 's1')); // same hold -> same pose
  assert.notDeepEqual(a, wobbleAt(stepMs + 1, 's1')); // next hold -> new pose
  assert.notDeepEqual(a, wobbleAt(10, 's2')); // different seed -> different pose
  for (let t = 0; t < 3000; t += 33) {
    const w = wobbleAt(t, 'x');
    assert.ok(Math.abs(w.dx) <= 1.5 && Math.abs(w.dy) <= 1.5 && Math.abs(w.rot) <= 0.5);
  }
});
