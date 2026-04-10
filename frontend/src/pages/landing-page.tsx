import { SignInButton, SignUpButton, useAuth, useUser } from "@clerk/clerk-react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  BrainCircuit,
  BriefcaseBusiness,
  CheckCircle2,
  FilePenLine,
  Gauge,
  Rows3,
  Sparkles,
  Target,
} from "lucide-react";

import { Logo } from "@/components/logo";
import { Button, Card, buttonClasses } from "@/components/ui";
import { describeApiError } from "@/lib/api/client";
import { useJobsQuery, useProfileQuery } from "@/lib/api/hooks";
import { buildDashboardMetrics, humanizeStatus } from "@/lib/jobs";

export function LandingPage() {
  const { isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const jobsQuery = useJobsQuery({ enabled: isLoaded && isSignedIn });
  const profileQuery = useProfileQuery({ enabled: isLoaded && isSignedIn });
  const latestJob = jobsQuery.data?.[0];
  const metrics = buildDashboardMetrics(jobsQuery.data ?? []);
  const workspaceTarget = profileQuery.data ? "/app/dashboard" : "/app/onboarding";
  const viewerName = profileQuery.data?.display_name || user?.firstName || "there";

  return (
    <div className="page-shell px-4 py-5 md:px-6 md:py-6">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-5">
        <header className="glass-panel animate-rise flex flex-col gap-4 rounded-[30px] border border-[var(--line)] px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <Logo size={36} />
            <div>
              <p className="hero-title text-2xl text-[var(--page-ink)]">Applyflow</p>
              <p className="text-sm text-[var(--muted-ink)]">One place to evaluate roles, write better letters, and track the search.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <a href="#features" className={buttonClasses("ghost")}>
              Features
            </a>
            <a href="#workflow" className={buttonClasses("ghost")}>
              Workflow
            </a>
            {isLoaded && isSignedIn ? (
              <Link to={workspaceTarget} className={buttonClasses("accent")}>
                {profileQuery.data ? "Open workspace" : "Finish setup"} <ArrowRight size={16} />
              </Link>
            ) : (
              <>
                <SignInButton mode="modal">
                  <Button type="button" variant="secondary">
                    Sign in
                  </Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button type="button">Get started</Button>
                </SignUpButton>
              </>
            )}
          </div>
        </header>

        <section className="glass-panel grain-overlay relative overflow-hidden rounded-[36px] border border-[var(--line)] px-6 py-8 md:px-10 md:py-12">
          <div className="absolute -left-10 top-10 h-32 w-32 rounded-full bg-[rgba(15,118,110,0.12)] blur-2xl animate-float-soft" />
          <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-[rgba(245,158,11,0.16)] blur-3xl animate-float-soft" />
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_450px] lg:items-center">
            <div className="space-y-6 animate-rise">
              <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">Focused job search system</p>
              <div className="space-y-4">
                <h1 className="hero-title max-w-4xl text-5xl leading-tight text-[var(--page-ink)] md:text-7xl">
                  Stay sharp through the whole application process.
                </h1>
                <p className="max-w-2xl text-lg leading-8 text-[var(--muted-ink)]">
                  Save your real profile once, score roles with more honesty, generate cleaner letters, and keep your whole pipeline visible without juggling notes, tabs, and half-finished drafts.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {isLoaded && isSignedIn ? (
                  <Link to={workspaceTarget} className={buttonClasses("accent")}>
                    {profileQuery.data ? "Return to your dashboard" : "Complete your setup"} <ArrowRight size={16} />
                  </Link>
                ) : (
                  <>
                    <SignUpButton mode="modal">
                      <Button type="button">Start your workspace</Button>
                    </SignUpButton>
                    <SignInButton mode="modal">
                      <Button type="button" variant="secondary">
                        Continue your search
                      </Button>
                    </SignInButton>
                  </>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { value: "1 profile", label: "that keeps your stable context consistent" },
                  { value: "Honest", label: "scoring that rewards proof, not wishful thinking" },
                  { value: "Clear", label: "status tracking from wishlist to offer" },
                ].map((item) => (
                  <div key={item.label} className="rounded-[22px] border border-[var(--line)] bg-white/72 p-4">
                    <p className="hero-title text-3xl text-[var(--page-ink)]">{item.value}</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="animate-rise-delay">
              {isLoaded && isSignedIn ? (
                <Card className="animate-float-soft border-[rgba(15,118,110,0.18)] bg-[linear-gradient(160deg,rgba(243,252,249,0.96)_0%,rgba(255,249,236,0.98)_100%)] p-6 md:p-7">
                  <div className="space-y-5">
                    <div className="rounded-[24px] border border-[rgba(15,118,110,0.15)] bg-white/78 px-5 py-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">Welcome back</p>
                      {jobsQuery.isPending ? (
                        <p className="mt-3 text-sm leading-6 text-[var(--muted-ink)]">Loading the latest shape of your search…</p>
                      ) : jobsQuery.isError ? (
                        <>
                          <p className="mt-3 text-xl font-semibold text-[var(--page-ink)]">We could not load your roles yet</p>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">{describeApiError(jobsQuery.error)}</p>
                        </>
                      ) : !profileQuery.data ? (
                        <>
                          <p className="mt-3 text-xl font-semibold text-[var(--page-ink)]">Let’s finish your foundation, {viewerName}</p>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                            Add your resume and honest context first, then the dashboard can score roles against something real.
                          </p>
                        </>
                      ) : latestJob ? (
                        <>
                          <p className="mt-3 text-xl font-semibold text-[var(--page-ink)]">
                            {latestJob.role_title || "Untitled role"} · {latestJob.company || "Unknown company"}
                          </p>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                            Latest status: {humanizeStatus(latestJob.current_status)}. You currently have {jobsQuery.data?.length || 0} role(s) in motion, {viewerName}.
                          </p>
                        </>
                      ) : (
                        <>
                          <p className="mt-3 text-xl font-semibold text-[var(--page-ink)]">Your workspace is ready for the first role</p>
                          <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                            Your profile is in place. Create the first job and the workspace will start reflecting the real shape of your search.
                          </p>
                        </>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: "Tracked roles", value: String(metrics.total) },
                        { label: "Interviews", value: String(metrics.interviewing) },
                        { label: "Waiting", value: String(metrics.waiting) },
                        { label: "Offers", value: String(metrics.offers) },
                      ].map((item) => (
                        <div key={item.label} className="rounded-[20px] border border-[var(--line)] bg-white/78 p-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted-ink)]">{item.label}</p>
                          <p className="mt-2 text-3xl font-semibold text-[var(--page-ink)]">{item.value}</p>
                        </div>
                      ))}
                    </div>

                    <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                      <div className="rounded-[20px] border border-[rgba(15,118,110,0.15)] bg-white/72 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">Next move</p>
                        <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
                          {profileQuery.data
                            ? latestJob
                              ? "Open the workspace to score, write, or update the current application stage."
                              : "Open the workspace to add your first role and start tracking the search."
                            : "Open onboarding to save the resume and context snapshot the whole workflow depends on."}
                        </p>
                      </div>
                      <Link to={workspaceTarget} className={buttonClasses("accent")}>
                        {profileQuery.data ? "Open workspace" : "Finish setup"}
                      </Link>
                    </div>
                  </div>
                </Card>
              ) : (
                <Card className="animate-float-soft bg-[var(--panel-strong)] p-6 md:p-7">
                  <div className="space-y-5">
                    <div className="rounded-[24px] bg-stone-950 px-5 py-5 text-stone-50">
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-300">What you get</p>
                      <p className="mt-3 text-xl font-semibold">A calmer system around real applications</p>
                      <p className="mt-2 text-sm leading-6 text-stone-300">
                        Keep the quality of your decisions high while making the work itself easier to return to every day.
                      </p>
                    </div>
                    <div className="grid gap-4">
                      {[
                        {
                          icon: BrainCircuit,
                          title: "Honest fit scoring",
                          description: "See where a role truly aligns with your background and where the paper gaps are still real.",
                        },
                        {
                          icon: FilePenLine,
                          title: "Letters that stay human",
                          description: "Generate concise, one-page cover letters with a cleaner structure and stronger voice.",
                        },
                        {
                          icon: Rows3,
                          title: "A pipeline you can trust",
                          description: "Track each application from wishlist to offer without losing context or momentum.",
                        },
                      ].map((item) => {
                        const Icon = item.icon;
                        return (
                          <div key={item.title} className="flex items-start gap-4 rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
                            <div className="rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]">
                              <Icon size={18} />
                            </div>
                            <div className="space-y-1">
                              <p className="font-semibold text-[var(--page-ink)]">{item.title}</p>
                              <p className="text-sm leading-6 text-[var(--muted-ink)]">{item.description}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </section>

        <section id="features" className="grid gap-5 lg:grid-cols-3">
          {[
            {
              icon: Target,
              title: "Decide with more honesty",
              description: "Use your real resume and context to judge whether a role is actually worth your energy.",
            },
            {
              icon: Gauge,
              title: "See momentum quickly",
              description: "Track interviews, waiting roles, and offers without reconstructing the story every time.",
            },
            {
              icon: Sparkles,
              title: "Write from signal, not panic",
              description: "Turn the strongest fit evidence into better cover letters instead of starting from scratch each time.",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title} className="animate-rise space-y-4 p-6">
                <div className="w-fit rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]">
                  <Icon size={20} />
                </div>
                <h2 className="text-2xl font-semibold text-[var(--page-ink)]">{item.title}</h2>
                <p className="text-sm leading-7 text-[var(--muted-ink)]">{item.description}</p>
              </Card>
            );
          })}
        </section>

        <section id="workflow" className="glass-panel rounded-[34px] border border-[var(--line)] px-6 py-8 md:px-10 md:py-10">
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">How it works</p>
              <h2 className="hero-title text-4xl text-[var(--page-ink)] md:text-5xl">A cleaner loop from first look to final decision</h2>
              <p className="max-w-3xl text-base leading-8 text-[var(--muted-ink)]">
                The goal is not just to generate content. It is to make the whole application process easier to evaluate, continue, and revisit.
              </p>
            </div>

            <div className="grid gap-5 lg:grid-cols-3">
              {[
                {
                  icon: CheckCircle2,
                  step: "01",
                  title: "Save your stable context",
                  description: "Keep one profile with the resume and honest context you actually want every future application to reflect.",
                },
                {
                  icon: BriefcaseBusiness,
                  step: "02",
                  title: "Bring in the real role",
                  description: "Create a role with the full description, the company context, and the application stage you want to track.",
                },
                {
                  icon: FilePenLine,
                  step: "03",
                  title: "Evaluate, write, and move",
                  description: "Score the role, generate the letter, update the status, and keep the next decision visible.",
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.step} className="rounded-[26px] border border-[var(--line)] bg-white/78 p-6">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">{item.step}</span>
                      <div className="rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]">
                        <Icon size={18} />
                      </div>
                    </div>
                    <h3 className="mt-5 text-2xl font-semibold text-[var(--page-ink)]">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted-ink)]">{item.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <footer className="px-2 pb-6 pt-2 text-sm text-[var(--muted-ink)]">
          <div className="flex flex-col gap-3 border-t border-[var(--line)] pt-5 md:flex-row md:items-center md:justify-between">
            <p>Applyflow is built for people who want a better system around applying, not more noise around it.</p>
            <div className="flex items-center gap-4">
              <a href="#features">Features</a>
              <a href="#workflow">Workflow</a>
              {isLoaded && isSignedIn ? <Link to="/app/dashboard">Dashboard</Link> : null}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
