/** CloudiQS enterprise mark — rounded tile with abstract CQ monogram. */
export function HelioLogo({
  className,
  size = 28,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id="bakeryCqLogoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8728F5" />
          <stop offset="55%" stopColor="#B02AEF" />
          <stop offset="100%" stopColor="#E82D96" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#bakeryCqLogoGrad)" />
      {/* C — open arc */}
      <path
        d="M15 9.6C11.35 9.6 8.7 12.4 8.7 16s2.65 6.4 6.3 6.4c1.3 0 2.45-.4 3.35-1.05"
        stroke="#FFFFFF"
        strokeWidth="2.55"
        strokeLinecap="round"
        fill="none"
      />
      {/* Q — ring + tail */}
      <circle
        cx="20.35"
        cy="16"
        r="5.2"
        stroke="#FFFFFF"
        strokeWidth="2.55"
        fill="none"
      />
      <path
        d="M23.7 19.7L26.15 22.4"
        stroke="#FFFFFF"
        strokeWidth="2.55"
        strokeLinecap="round"
      />
    </svg>
  );
}
