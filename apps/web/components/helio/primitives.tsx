"use client";

import { forwardRef, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export function Surface({
  className,
  elevated,
  ...props
}: HTMLAttributes<HTMLDivElement> & { elevated?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-[var(--surface)] border border-[var(--stroke)]",
        elevated && "shadow-raised",
        className
      )}
      {...props}
    />
  );
}

export function Eyebrow({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn(
        "text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--ink-tertiary)]",
        className
      )}
      {...props}
    />
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
  gradient,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  gradient?: boolean;
}) {
  if (gradient) {
    return (
      <div
        className={cn(
          "rounded-2xl bg-brand-gradient text-white px-5 py-5 sm:px-7 sm:py-6 shadow-raised",
          className
        )}
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0 space-y-2">
            {eyebrow ? (
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/75">
                {eyebrow}
              </p>
            ) : null}
            <h1 className="text-[26px] sm:text-[34px] font-semibold tracking-[-0.035em] leading-[1.12]">
              {title}
            </h1>
            {description ? (
              <p className="text-sm sm:text-[15px] text-white/85 max-w-2xl leading-relaxed">
                {description}
              </p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0 space-y-2">
        {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
        <h1 className="text-[26px] sm:text-[34px] font-semibold tracking-[-0.035em] text-[var(--ink)] leading-[1.12]">
          {title}
        </h1>
        {description ? (
          <p className="text-sm sm:text-[15px] text-[var(--ink-secondary)] max-w-2xl leading-relaxed">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
    </div>
  );
}

type BtnVariant = "primary" | "secondary" | "quiet" | "destructive";

export const HelioButton = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: BtnVariant;
    loading?: boolean;
    size?: "sm" | "md" | "lg" | "icon";
  }
>(function HelioButton(
  { className, variant = "primary", loading, disabled, size = "md", children, ...props },
  ref
) {
  const sizes = {
    sm: "h-9 px-3 text-sm rounded-[10px]",
    md: "h-11 px-4 text-sm rounded-xl",
    lg: "h-12 px-5 text-[15px] rounded-xl",
    icon: "h-10 w-10 rounded-xl",
  };
  const variants: Record<BtnVariant, string> = {
    primary:
      "bg-brand-gradient text-white shadow-soft hover:brightness-105 disabled:opacity-50",
    secondary:
      "bg-[var(--surface)] text-[var(--ink)] border border-[var(--stroke-strong)] hover:bg-[var(--signal-soft)] hover:border-[var(--signal)]",
    quiet:
      "bg-transparent text-[var(--ink-secondary)] hover:bg-[var(--signal-soft)] hover:text-[var(--ink)]",
    destructive:
      "bg-[var(--danger-soft)] text-[var(--danger)] hover:bg-[var(--danger)] hover:text-white",
  };
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--signal)] focus-visible:ring-offset-2 disabled:pointer-events-none",
        sizes[size],
        variants[variant],
        className
      )}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      {children}
    </button>
  );
});

export function StatusChip({
  tone = "neutral",
  children,
  className,
}: {
  tone?: "neutral" | "success" | "warning" | "danger" | "signal" | "info";
  children: ReactNode;
  className?: string;
}) {
  const tones = {
    neutral: "bg-[var(--surface-soft)] text-[var(--ink-secondary)]",
    success: "bg-[var(--success-soft)] text-[var(--success)]",
    warning: "bg-[var(--warning-soft)] text-[var(--warning)]",
    danger: "bg-[var(--danger-soft)] text-[var(--danger)]",
    signal: "bg-[var(--signal-soft)] text-[var(--signal)]",
    info: "bg-[color-mix(in_srgb,var(--info-blue)_12%,white)] text-[var(--info-blue)]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
  className,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex p-1 rounded-xl bg-[var(--surface-soft)] border border-[var(--stroke)]",
        className
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "px-3.5 py-1.5 text-sm rounded-[10px] transition-colors",
              active
                ? "bg-[var(--surface)] text-[var(--signal)] shadow-soft font-medium"
                : "text-[var(--ink-secondary)] hover:text-[var(--ink)]"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("text-center py-12 px-6", className)}>
      <p className="text-[15px] font-medium text-[var(--ink)]">{title}</p>
      {description ? (
        <p className="mt-2 text-sm text-[var(--ink-secondary)] max-w-md mx-auto">{description}</p>
      ) : null}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  className,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-[var(--danger-soft)] bg-[var(--danger-soft)]/40 p-6", className)}>
      <p className="font-medium text-[var(--danger)]">{title}</p>
      {description ? <p className="mt-1 text-sm text-[var(--ink-secondary)]">{description}</p> : null}
      {onRetry ? (
        <HelioButton variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Retry
        </HelioButton>
      ) : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-[var(--surface-soft)]", className)} />;
}

export function DemoIndicator({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1 text-[11px] text-[var(--ink-secondary)]",
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--magenta)]" aria-hidden />
      Demo environment · Simulated enterprise data
    </div>
  );
}
