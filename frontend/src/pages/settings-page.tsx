import { Link } from "@tanstack/react-router";
import { Bell, FileText, ShieldCheck, SlidersHorizontal } from "lucide-react";

import { Card, PageHeader, buttonClasses } from "@/components/ui";

export function SettingsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Preferences"
        title="Make Applyflow feel like your workspace"
        description="Adjust the parts of the application rhythm that matter day to day: how you review roles, maintain your profile, and keep the search moving."
        backTo="/app/dashboard"
        backLabel="Back to dashboard"
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="space-y-5">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]">
              <SlidersHorizontal size={20} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[var(--page-ink)]">Workspace defaults</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
                These preferences are coming next. For now, Applyflow keeps the defaults simple and consistent.
              </p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {[
              { label: "Default role stage", value: "Waiting" },
              { label: "Score style", value: "Honest" },
              { label: "Letter length", value: "One page" },
            ].map((item) => (
              <div key={item.label} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted-ink)]">{item.label}</p>
                <p className="mt-2 text-lg font-semibold text-[var(--page-ink)]">{item.value}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="space-y-4 bg-[linear-gradient(160deg,rgba(243,252,249,0.96)_0%,rgba(255,249,236,0.98)_100%)]">
          <div className="rounded-2xl bg-white/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent)]">Next best action</p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
              Keep your profile fresh. Every future score and cover letter depends on that snapshot.
            </p>
          </div>
          <Link to="/app/profile" className={buttonClasses("accent")}>
            Update profile
          </Link>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {[
          {
            icon: FileText,
            title: "Profile source",
            description: "Your resume and honest context are versioned so old evaluations stay reproducible.",
            action: "Edit profile",
            to: "/app/profile" as const,
          },
          {
            icon: Bell,
            title: "Follow-up rhythm",
            description: "Reminder controls are not enabled yet, but the pipeline keeps waiting roles visible.",
            action: "Open pipeline",
            to: "/app/jobs" as const,
          },
          {
            icon: ShieldCheck,
            title: "Private by default",
            description: "Jobs, scores, and letters live in your workspace. Google export is not required for the web app.",
            action: "View letters",
            to: "/app/letters" as const,
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title} className="space-y-4">
              <div className="w-fit rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]">
                <Icon size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[var(--page-ink)]">{item.title}</h2>
                <p className="mt-2 text-sm leading-7 text-[var(--muted-ink)]">{item.description}</p>
              </div>
              <Link to={item.to} className={buttonClasses("secondary")}>
                {item.action}
              </Link>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
