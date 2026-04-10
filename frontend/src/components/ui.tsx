import { clsx } from "clsx";
import { ArrowLeft, LoaderCircle, Sparkles } from "lucide-react";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

import { humanizeStatus } from "@/lib/jobs";
import type { ApplicationStatus } from "@/lib/api/types";

export function buttonClasses(variant: "primary" | "secondary" | "ghost" | "accent" = "primary") {
  return clsx(
    "inline-flex cursor-pointer items-center justify-center rounded-full px-4 py-2 text-sm font-semibold transition duration-150",
    variant === "primary" &&
      "bg-[var(--page-ink)] text-white shadow-[0_12px_24px_rgba(27,35,52,0.14)] hover:-translate-y-0.5",
    variant === "accent" &&
      "bg-[var(--accent)] text-white shadow-[0_14px_28px_rgba(15,118,110,0.22)] hover:-translate-y-0.5",
    variant === "secondary" &&
      "border border-[var(--line)] bg-white/80 text-[var(--page-ink)] hover:border-[var(--accent)] hover:text-[var(--accent)]",
    variant === "ghost" && "text-[var(--muted-ink)] hover:text-[var(--page-ink)]",
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "accent" }) {
  return <button className={clsx(buttonClasses(variant), className)} {...props} />;
}

export function BackButton({
  label = "Back",
  fallbackPath = "/app/dashboard",
  className,
}: {
  label?: string;
  fallbackPath?: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={clsx(
        buttonClasses("ghost"),
        "group w-fit gap-2 border border-transparent bg-white/50 px-3 text-[var(--page-ink)] hover:border-[var(--line)] hover:bg-white/80",
        className,
      )}
      onClick={() => {
        if (window.history.length > 1) {
          window.history.back();
          return;
        }
        window.location.assign(fallbackPath);
      }}
      aria-label={label}
    >
      <ArrowLeft size={16} className="transition group-hover:-translate-x-0.5" />
      <span>{label}</span>
    </button>
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("glass-panel rounded-[28px] border border-[var(--line)] p-6", className)} {...props} />;
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-[var(--page-ink)]">
      <span>{label}</span>
      {children}
      {hint ? <span className="text-xs text-[var(--muted-ink)]">{hint}</span> : null}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        "rounded-2xl border border-[var(--line)] bg-white/90 px-4 py-3 text-sm text-[var(--page-ink)] outline-none transition focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]",
        props.className,
      )}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={clsx(
        "min-h-36 rounded-[24px] border border-[var(--line)] bg-white/90 px-4 py-3 text-sm text-[var(--page-ink)] outline-none transition focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]",
        props.className,
      )}
    />
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={clsx(
        "rounded-2xl border border-[var(--line)] bg-white/90 px-4 py-3 text-sm text-[var(--page-ink)] outline-none transition focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]",
        props.className,
      )}
    />
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
  backTo,
  backLabel = "Back",
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
  backTo?: string;
  backLabel?: string;
}) {
  return (
    <div className="space-y-4">
      {backTo ? <BackButton fallbackPath={backTo} label={backLabel} /> : null}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl space-y-3">
          {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">{eyebrow}</p> : null}
          <h1 className="hero-title text-4xl leading-tight text-[var(--page-ink)] md:text-5xl">{title}</h1>
          <p className="text-base leading-7 text-[var(--muted-ink)]">{description}</p>
        </div>
        {action}
      </div>
    </div>
  );
}

export function StatusPill({ status }: { status: ApplicationStatus }) {
  const tone =
    status === "accepted"
      ? "bg-emerald-100 text-emerald-800"
      : status === "offer"
        ? "bg-teal-100 text-teal-800"
        : status === "interviewing" || status === "final round" || status === "interview scheduled"
          ? "bg-amber-100 text-amber-800"
          : status === "rejected" || status === "withdrawn"
            ? "bg-rose-100 text-rose-700"
            : "bg-stone-100 text-stone-700";

  return (
    <span className={clsx("inline-flex rounded-full px-3 py-1 text-xs font-semibold", tone)}>
      {humanizeStatus(status)}
    </span>
  );
}

export function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 85 ? "bg-emerald-100 text-emerald-800" : score >= 70 ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-700";
  return <span className={clsx("inline-flex rounded-full px-3 py-1 text-xs font-semibold", tone)}>{score}/100</span>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="space-y-3 border-dashed">
      <h2 className="text-lg font-semibold text-[var(--page-ink)]">{title}</h2>
      <p className="text-sm leading-6 text-[var(--muted-ink)]">{description}</p>
      {action}
    </Card>
  );
}

export function LoadingState({
  title = "Loading",
  description = "Preparing your workspace.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <Card className="relative overflow-hidden p-7">
      <div className="absolute right-5 top-5 h-20 w-20 rounded-full bg-[var(--accent-soft)] blur-2xl" />
      <div className="relative flex items-center gap-4">
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[var(--page-ink)] text-white shadow-[0_18px_34px_rgba(27,35,52,0.14)]">
          <LoaderCircle size={22} className="animate-spin" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-[var(--accent)]" />
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent)]">Working</p>
          </div>
          <h2 className="mt-1 text-lg font-semibold text-[var(--page-ink)]">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">{description}</p>
        </div>
      </div>
    </Card>
  );
}
