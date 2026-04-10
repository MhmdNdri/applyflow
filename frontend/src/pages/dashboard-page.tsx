import { Link } from "@tanstack/react-router";

import { Card, EmptyState, PageHeader, ScorePill, StatusPill, buttonClasses } from "@/components/ui";
import { describeApiError } from "@/lib/api/client";
import { useJobsQuery, useProfileQuery } from "@/lib/api/hooks";
import {
  buildDashboardActions,
  buildDashboardMetrics,
  buildJobWorkflowSummary,
  findActiveWorkflowJobs,
  findBestFitJob,
  formatTimestamp,
  humanizeTaskType,
} from "@/lib/jobs";

export function DashboardPage() {
  const profileQuery = useProfileQuery({ enabled: true });
  const jobsQuery = useJobsQuery({ enabled: true });

  if (jobsQuery.isPending || profileQuery.isPending) {
    return <div className="text-sm text-[var(--muted-ink)]">Loading dashboard…</div>;
  }

  if (jobsQuery.isError) {
    return (
      <EmptyState
        title="Dashboard data could not load"
        description={`Jobs API error: ${describeApiError(jobsQuery.error)}`}
      />
    );
  }

  const jobs = jobsQuery.data ?? [];
  const metrics = buildDashboardMetrics(jobs);
  const actions = buildDashboardActions(jobs);
  const recentJobs = jobs.slice(0, 4);
  const bestFitJob = findBestFitJob(jobs);
  const workflowJobs = findActiveWorkflowJobs(jobs).slice(0, 3);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Your application rhythm"
        description="See where the search stands today, which roles need attention next, and how the internal tracker and saved letters are evolving."
        action={
          <div className="flex flex-wrap gap-3">
            <Link to="/app/jobs" className={buttonClasses("secondary")}>
              Open pipeline
            </Link>
            <Link to="/app/letters" className={buttonClasses("ghost")}>
              Letters
            </Link>
            <Link to="/app/profile" className={buttonClasses("ghost")}>
              Profile
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {[
          { label: "Total roles", value: metrics.total, tone: "text-[var(--page-ink)]" },
          { label: "Scored roles", value: metrics.scored, tone: "text-[var(--accent)]" },
          { label: "Need first score", value: metrics.needsScoring, tone: "text-[var(--warn)]" },
          { label: "In interviews", value: metrics.interviewing, tone: "text-amber-700" },
          { label: "Active AI tasks", value: metrics.activeTasks, tone: "text-teal-700" },
        ].map((metric) => (
          <Card key={metric.label} className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">{metric.label}</p>
            <p className={`hero-title text-4xl ${metric.tone}`}>{metric.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_360px]">
        <Card className="space-y-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-[var(--page-ink)]">Recent applications</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
                Reopen the latest roles with their score and workflow state still attached.
              </p>
            </div>
            <Link to="/app/jobs" className={buttonClasses("ghost")}>
              See all
            </Link>
          </div>

          {recentJobs.length === 0 ? (
            <EmptyState
              title="No jobs yet"
              description="Create your first job on the Jobs page to start filling the dashboard with live data."
              action={
                <Link to="/app/jobs" className={buttonClasses("primary")}>
                  Create a job
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <Link
                  key={job.id}
                  to="/app/jobs/$jobId"
                  params={{ jobId: job.id }}
                  className="block rounded-[24px] border border-[var(--line)] bg-white/75 p-4 transition hover:-translate-y-0.5 hover:border-[var(--accent)]"
                >
                  <div className="flex flex-col gap-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-1">
                        <p className="text-lg font-semibold text-[var(--page-ink)]">
                          {job.role_title || "Untitled role"} · {job.company || "Unknown company"}
                        </p>
                        <p className="text-sm text-[var(--muted-ink)]">{job.location || "Location not added"}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusPill status={job.current_status} />
                        {job.latest_evaluation ? <ScorePill score={job.latest_evaluation.score} /> : null}
                      </div>
                    </div>
                    <div className="rounded-[18px] bg-stone-100 px-4 py-3 text-sm text-[var(--muted-ink)]">
                      {buildJobWorkflowSummary(job)}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-5">
          <Card className="space-y-4">
            <h2 className="text-xl font-semibold text-[var(--page-ink)]">Best current fit</h2>
            {bestFitJob?.latest_evaluation ? (
              <div className="space-y-4">
                <div className="rounded-[22px] border border-[rgba(15,118,110,0.16)] bg-[var(--accent-soft)] p-4">
                  <p className="text-sm font-semibold text-[var(--page-ink)]">
                    {bestFitJob.role_title || "Untitled role"} · {bestFitJob.company || "Unknown company"}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <ScorePill score={bestFitJob.latest_evaluation.score} />
                    <StatusPill status={bestFitJob.current_status} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-ink)]">{bestFitJob.latest_evaluation.feedback}</p>
                </div>
                <Link to="/app/jobs/$jobId" params={{ jobId: bestFitJob.id }} className={buttonClasses("secondary")}>
                  Open best-fit role
                </Link>
              </div>
            ) : (
              <EmptyState
                title="No scored roles yet"
                description="Run the first browser score task on a job detail page and this card will surface the strongest match."
              />
            )}
          </Card>

          <Card className="space-y-4">
            <h2 className="text-xl font-semibold text-[var(--page-ink)]">Profile pulse</h2>
            <p className="text-sm leading-6 text-[var(--muted-ink)]">
              Keep the exact snapshot future evaluations will use visible while you work.
            </p>
            {profileQuery.data ? (
              <div className="space-y-4">
                <div className="rounded-[22px] border border-[var(--line)] bg-white/80 p-4">
                  <p className="font-semibold text-[var(--page-ink)]">{profileQuery.data.display_name || "Applicant"}</p>
                  <p className="mt-2 text-sm text-[var(--muted-ink)]">{profileQuery.data.location || "Location not set"}</p>
                  {profileQuery.data.resume_source_file ? (
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">
                      Resume source · {profileQuery.data.resume_source_file.file_name}
                    </p>
                  ) : null}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-[20px] bg-stone-100 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">Resume version</p>
                    <p className="mt-2 text-2xl font-semibold text-[var(--page-ink)]">{profileQuery.data.resume_version_number}</p>
                  </div>
                  <div className="rounded-[20px] bg-stone-100 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">Context version</p>
                    <p className="mt-2 text-2xl font-semibold text-[var(--page-ink)]">{profileQuery.data.context_version_number}</p>
                  </div>
                </div>
                <Link to="/app/profile" className={buttonClasses("secondary")}>
                  Edit profile
                </Link>
              </div>
            ) : (
              <EmptyState title="Profile unavailable" description="Complete onboarding to start using the browser workspace." />
            )}
          </Card>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_360px]">
        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--page-ink)]">Suggested next moves</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {actions.map((item) => (
              <div key={item.title} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
                <p className="font-semibold text-[var(--page-ink)]">{item.title}</p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">{item.description}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--page-ink)]">Workflow watch</h2>
          {workflowJobs.length === 0 ? (
            <EmptyState
              title="No active AI workflows"
              description="When a score or cover-letter task is queued, running, or fails, it will show up here."
            />
          ) : (
            <div className="space-y-3">
              {workflowJobs.map((job) => (
                <Link
                  key={job.id}
                  to="/app/jobs/$jobId"
                  params={{ jobId: job.id }}
                  className="block rounded-[22px] border border-[var(--line)] bg-white/75 p-4"
                >
                  <p className="font-semibold text-[var(--page-ink)]">
                    {job.role_title || "Untitled role"} · {job.company || "Unknown company"}
                  </p>
                  <p className="mt-2 text-sm text-[var(--muted-ink)]">
                    {job.latest_task ? `${humanizeTaskType(job.latest_task.task_type)} · ${job.latest_task.status}` : "No recent task"}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">
                    {formatTimestamp(job.latest_task?.updated_at || job.updated_at)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
