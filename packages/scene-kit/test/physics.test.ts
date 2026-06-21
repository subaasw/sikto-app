import assert from 'node:assert';
import { test } from 'node:test';
import { DT, poseAt, pt, simulate, type DriveFn, type Stick } from '../src/physics.ts';

// A pendulum: a pinned anchor + a bob, started off-axis so gravity swings it.
const anchor = () => pt(0, 0, true);
const bob = () => pt(8, 6); // distance 10 from the anchor
const sticks: Stick[] = [[0, 1, 10]];
const noDrive: DriveFn = (_t, pts) => pts.map(() => ({ x: 0, y: 0 }));

const dist = (pose: { x: number; y: number }[], a: number, b: number) =>
  Math.hypot(pose[b].x - pose[a].x, pose[b].y - pose[a].y);

test('deterministic: identical inputs → identical trajectory', () => {
  const a = simulate([anchor(), bob()], sticks, noDrive, 2000);
  const b = simulate([anchor(), bob()], sticks, noDrive, 2000);
  assert.deepEqual(a, b);
});

test('constraint holds: bone length stays ~10 throughout', () => {
  const traj = simulate([anchor(), bob()], sticks, noDrive, 3000);
  for (const pose of traj) {
    assert.ok(Math.abs(dist(pose, 0, 1) - 10) < 0.5, `len ${dist(pose, 0, 1)}`);
  }
});

test('it actually moves (gravity swings the bob)', () => {
  const traj = simulate([anchor(), bob()], sticks, noDrive, 2000);
  const start = traj[0][1];
  const later = traj[Math.floor(traj.length / 2)][1];
  assert.ok(Math.hypot(later.x - start.x, later.y - start.y) > 1);
});

test('pinned point never moves', () => {
  const traj = simulate([anchor(), bob()], sticks, noDrive, 1500);
  for (const pose of traj) {
    assert.equal(pose[0].x, 0);
    assert.equal(pose[0].y, 0);
  }
});

test('stays stable (no divergence/NaN) over a long run', () => {
  const traj = simulate([anchor(), bob()], sticks, noDrive, 10_000);
  const last = traj[traj.length - 1];
  assert.ok(Number.isFinite(last[1].x) && Math.hypot(last[1].x, last[1].y) < 100);
});

test('poseAt interpolates between steps', () => {
  const traj = simulate([anchor(), bob()], sticks, noDrive, 1000);
  const mid = poseAt(traj, DT * 1.5);
  const lo = traj[1][1];
  const hi = traj[2][1];
  assert.ok(mid[1].x >= Math.min(lo.x, hi.x) - 1e-6 && mid[1].x <= Math.max(lo.x, hi.x) + 1e-6);
});

test('a spring drive pulls a point toward its target', () => {
  // free point at (0,0), pulled toward (20,0) by a spring; pinned anchor unused.
  const drive: DriveFn = (_t, pts) => [
    { x: 0, y: 0 },
    { x: (20 - pts[1].x) * 0.02, y: (0 - pts[1].y) * 0.02 },
  ];
  const traj = simulate([pt(-50, 0, true), pt(0, 0)], [], drive, 4000, { gravity: 0 });
  assert.ok(traj[traj.length - 1][1].x > 12, 'should approach x=20');
});
