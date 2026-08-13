/**
 * A hand holding a marker, drawn inline (no external asset → identical in the
 * browser and Remotion's headless Chrome). The marker tip sits at the SVG
 * origin (~8,8), so positioning the component at the wipe's leading edge puts
 * the nib exactly where the ink is being laid down.
 */
export function Hand({ x, y, size = 13, color }: { x: number; y: number; size?: number; color: string }) {
  // x,y are stage-percent of the marker tip (the wipe's leading edge).
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        width: `${size}cqw`,
        height: `${size}cqw`,
        pointerEvents: 'none',
        zIndex: 50,
        filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.18))',
      }}
    >
      <svg viewBox="0 0 100 100" width="100%" height="100%" aria-hidden>
        {/* marker barrel: nib at top-left (8,8) down to the grip */}
        <polygon points="8,8 20,4 64,48 52,60" fill={color} />
        {/* nib */}
        <polygon points="8,8 18,11 11,18" fill="#1f2530" />
        {/* barrel highlight */}
        <polygon points="14,9 20,7 60,47 56,51" fill="#ffffff" opacity="0.22" />
        {/* hand: palm blob gripping the lower barrel */}
        <path
          d="M48,52 C58,46 72,50 80,60 C88,70 86,86 74,92 C62,98 46,94 42,82 C39,73 40,58 48,52 Z"
          fill="#e8b48c"
        />
        {/* finger ridges over the grip */}
        <path d="M50,58 C58,55 66,57 71,63" stroke="#cf9468" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M48,67 C57,64 66,66 72,72" stroke="#cf9468" strokeWidth="3" fill="none" strokeLinecap="round" />
      </svg>
    </div>
  );
}
