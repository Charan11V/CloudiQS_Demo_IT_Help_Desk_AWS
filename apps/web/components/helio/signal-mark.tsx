import { cn } from "@/lib/utils";

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
      className={cn("shrink-0", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id="cqLogoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8728F5" />
          <stop offset="55%" stopColor="#B02AEF" />
          <stop offset="100%" stopColor="#E82D96" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#cqLogoGrad)" />
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

/** Soft abstract brand wash — kept minimal for any remaining editorial use. */
export function SignalIllustration({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 640 420"
      fill="none"
      className={cn("w-full h-auto", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id="sigSoft" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8728F5" stopOpacity="0.32" />
          <stop offset="50%" stopColor="#B02AEF" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#E82D96" stopOpacity="0.1" />
        </linearGradient>
      </defs>
      <rect x="170" y="85" width="300" height="250" rx="56" fill="url(#sigSoft)" />
      <rect
        x="230"
        y="130"
        width="180"
        height="160"
        rx="36"
        stroke="#FFFFFF"
        strokeWidth="2"
        opacity="0.22"
      />
    </svg>
  );
}
