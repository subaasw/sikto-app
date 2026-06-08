import { cn } from '@/lib/utils';

/**
 * Pixel-art graduation cap (mortarboard): button on top, wide diamond board,
 * tassel hanging on the right. Cap fill follows `currentColor`; the tassel uses
 * the lime primary so the mark reads on any surface.
 *
 * Grid is 13 x 9 cells. `.` = empty, `X` = filled.
 */
const CAP = [
  '......X......',
  '....XXXXX....',
  '..XXXXXXXXX..',
  '.XXXXXXXXXXX.',
  '..XXXXXXXXX..',
  '....XXXXX....',
  '.............',
  '.............',
  '.............',
];

const TASSEL = [
  '.............',
  '.............',
  '.............',
  '.............',
  '...........X.',
  '...........X.',
  '...........X.',
  '..........XXX',
  '...........X.',
];

function cells(map: string[]) {
  const out: { x: number; y: number }[] = [];
  map.forEach((row, y) =>
    row.split('').forEach((c, x) => {
      if (c === 'X') out.push({ x, y });
    }),
  );
  return out;
}

const capCells = cells(CAP);
const tasselCells = cells(TASSEL);

export function PixelLogo({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={(size * 9) / 13}
      viewBox="0 0 13 9"
      role="img"
      aria-label="Sikto"
      className={cn('pixelated', className)}
    >
      {capCells.map(({ x, y }) => (
        <rect key={`c-${x}-${y}`} x={x} y={y} width={1} height={1} fill="currentColor" />
      ))}
      {tasselCells.map(({ x, y }) => (
        <rect key={`t-${x}-${y}`} x={x} y={y} width={1} height={1} fill="var(--primary)" />
      ))}
    </svg>
  );
}
