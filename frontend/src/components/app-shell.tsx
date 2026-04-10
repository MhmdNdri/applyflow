import { SignInButton, SignUpButton, UserButton, useAuth, useUser } from "@clerk/clerk-react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { BriefcaseBusiness, FileText, LayoutDashboard, Settings2, Sparkles } from "lucide-react";
import { type ReactNode, startTransition, useEffect, useEffectEvent } from "react";

import { describeApiError } from "@/lib/api/client";
import { useAuthMeQuery, useJobsQuery, useProfileQuery, isApiError } from "@/lib/api/hooks";
import { buildDashboardMetrics } from "@/lib/jobs";

import { Button, Card, buttonClasses } from "./ui";

const navItems = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
  { label: "Pipeline", to: "/app/jobs", icon: BriefcaseBusiness },
  { label: "Letters", to: "/app/letters", icon: FileText },
  { label: "Profile", to: "/app/profile", icon: Sparkles },
  { label: "Settings", to: "/app/settings", icon: Settings2 },
] as const;

export function AppShell({
  title,
  description,
  allowMissingProfile = false,
  children,
}: {
  title: string;
  description: string;
  allowMissingProfile?: boolean;
  children: ReactNode;
}) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const navigate = useNavigate();
  const { isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const profileQuery = useProfileQuery({ enabled: isLoaded && isSignedIn });
  const authQuery = useAuthMeQuery({ enabled: isLoaded && isSignedIn });
  const jobsQuery = useJobsQuery({ enabled: isLoaded && isSignedIn });
  const pipeline = buildDashboardMetrics(jobsQuery.data ?? []);

  const syncProfileRouting = useEffectEvent(() => {
    if (!isLoaded || !isSignedIn) {
      return;
    }

    if (profileQuery.data && pathname === "/app/onboarding") {
      startTransition(() => {
        void navigate({ to: "/app/dashboard" });
      });
      return;
    }

    if (isApiError(profileQuery.error, 404) && !allowMissingProfile && pathname !== "/app/onboarding") {
      startTransition(() => {
        void navigate({ to: "/app/onboarding" });
      });
    }
  });

  useEffect(() => {
    syncProfileRouting();
  }, [allowMissingProfile, isLoaded, isSignedIn, pathname, profileQuery.data, profileQuery.error, syncProfileRouting]);

  if (!isLoaded) {
    return <FullPageMessage title="Loading your workspace" description="Checking your session and opening the latest application context." />;
  }

  if (!isSignedIn) {
    return <SignedOutState />;
  }

  if (profileQuery.isPending && !allowMissingProfile) {
    return <FullPageMessage title="Loading your profile" description="Checking the latest version of your saved resume and context." />;
  }

  if (profileQuery.isError && !isApiError(profileQuery.error, 404)) {
    return (
      <FullPageMessage
        title="The workspace could not load"
        description={`There was a problem loading your profile: ${describeApiError(profileQuery.error)}`}
      />
    );
  }

  const displayName = profileQuery.data?.display_name || user?.fullName || "Applicant";
  const email = authQuery.data?.email || user?.primaryEmailAddress?.emailAddress || "Signed in";

  return (
    <div className="page-shell px-4 py-5 md:px-6 md:py-6">
      <div className="mx-auto grid max-w-[1480px] gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="glass-panel grain-overlay relative min-w-0 rounded-[32px] border border-[var(--line)] p-6">
          <div className="min-w-0 space-y-8">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">Applyflow</p>
              <div className="min-w-0">
                <h1 className="hero-title text-3xl text-[var(--page-ink)]">Application cockpit</h1>
                <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                  Keep your roles, letters, status changes, and next moves in one place.
                </p>
              </div>
            </div>

            <Card className="min-w-0 space-y-2 overflow-hidden bg-[var(--panel-strong)] p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">Signed in as</p>
              <p className="truncate text-lg font-semibold text-[var(--page-ink)]">{displayName}</p>
              <p className="break-all text-sm leading-6 text-[var(--muted-ink)]">{email}</p>
            </Card>

            <nav className="space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname.startsWith(item.to);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={
                      active
                        ? "flex items-center gap-3 rounded-2xl border border-[rgba(15,118,110,0.18)] bg-[var(--accent-soft)] px-4 py-3 text-sm font-semibold text-[var(--page-ink)] shadow-[0_10px_20px_rgba(15,118,110,0.08)]"
                        : "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold text-[var(--muted-ink)] transition hover:bg-white/70 hover:text-[var(--page-ink)]"
                    }
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            <Card className="min-w-0 space-y-4 overflow-hidden bg-white/70 p-5">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">Pipeline snapshot</p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                  Keep the shape of the search visible, not just the last task you ran.
                </p>
              </div>
              {jobsQuery.isError ? (
                <p className="text-sm text-rose-700">{describeApiError(jobsQuery.error)}</p>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Roles", value: pipeline.total },
                    { label: "Interviews", value: pipeline.interviewing },
                    { label: "Waiting", value: pipeline.waiting },
                    { label: "Offers", value: pipeline.offers },
                  ].map((item) => (
                    <div key={item.label} className="min-w-0 rounded-[20px] bg-stone-100 p-3">
                      <p className="break-words text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted-ink)]">{item.label}</p>
                      <p className="mt-2 text-xl font-semibold text-[var(--page-ink)]">{item.value}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </aside>

        <main className="glass-panel rounded-[32px] border border-[var(--line)] p-6 md:p-8">
          <header className="mb-8 flex flex-col gap-5 border-b border-[var(--line)] pb-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">Workspace</p>
              <h2 className="hero-title text-4xl text-[var(--page-ink)]">{title}</h2>
              <p className="text-base leading-7 text-[var(--muted-ink)]">{description}</p>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/app/jobs" className={buttonClasses("secondary")}>
                Open pipeline
              </Link>
              <div className="rounded-full border border-[var(--line)] bg-white/80 p-1">
                <UserButton />
              </div>
            </div>
          </header>

          {children}
        </main>
      </div>
    </div>
  );
}

function FullPageMessage({ title, description }: { title: string; description: string }) {
  return (
    <div className="page-shell flex items-center justify-center px-4 py-10">
      <Card className="max-w-lg space-y-3 p-8 text-center">
        <h1 className="hero-title text-3xl text-[var(--page-ink)]">{title}</h1>
        <p className="text-sm leading-7 text-[var(--muted-ink)]">{description}</p>
      </Card>
    </div>
  );
}

function SignedOutState() {
  return (
    <div className="page-shell flex items-center justify-center px-4 py-10">
      <Card className="max-w-2xl space-y-5 p-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">Sign in required</p>
        <h1 className="hero-title text-4xl text-[var(--page-ink)]">Open your application workspace</h1>
        <p className="text-base leading-7 text-[var(--muted-ink)]">
          Sign in to manage your profile, track your roles, and keep your whole search in one place.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <SignInButton mode="modal">
            <Button type="button">Sign in</Button>
          </SignInButton>
          <SignUpButton mode="modal">
            <Button type="button" variant="secondary">
              Create account
            </Button>
          </SignUpButton>
        </div>
      </Card>
    </div>
  );
}
