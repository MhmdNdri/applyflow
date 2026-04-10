import { useForm } from "@tanstack/react-form";
import { Link, useParams } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button, Card, EmptyState, Field, PageHeader, ScorePill, Select, StatusPill, buttonClasses } from "@/components/ui";
import { describeApiError } from "@/lib/api/client";
import {
  useJobDetailQuery,
  useRegenerateCoverLetterMutation,
  useRetryTaskMutation,
  useScoreJobMutation,
  useTaskQuery,
  useUpdateJobStatusMutation,
} from "@/lib/api/hooks";
import type { BackgroundTaskResponse, JobDetailResponse } from "@/lib/api/types";
import { APPLICATION_STATUS_OPTIONS, formatTimestamp, humanizeStatus, humanizeTaskType, humanizeVerdict } from "@/lib/jobs";

export function JobDetailPage() {
  const { jobId } = useParams({ from: "/app/jobs/$jobId" });
  const jobQuery = useJobDetailQuery(jobId, { enabled: true });

  if (jobQuery.isPending) {
    return <div className="text-sm text-[var(--muted-ink)]">Loading job detail…</div>;
  }

  if (jobQuery.isError || !jobQuery.data) {
    return (
      <EmptyState
        title="Job detail unavailable"
        description={`The API could not load this role: ${describeApiError(jobQuery.error)}`}
      />
    );
  }

  return <JobDetailContent jobId={jobId} />;
}

function JobDetailContent({ jobId }: { jobId: string }) {
  const queryClient = useQueryClient();
  const jobQuery = useJobDetailQuery(jobId, { enabled: true });
  const updateStatus = useUpdateJobStatusMutation(jobId);
  const scoreJob = useScoreJobMutation(jobId);
  const regenerateCoverLetter = useRegenerateCoverLetterMutation(jobId);
  const retryTask = useRetryTaskMutation();
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);
  const [copiedLetter, setCopiedLetter] = useState(false);
  const job = jobQuery.data;

  const taskQuery = useTaskQuery(activeTaskId || "", {
    enabled: Boolean(activeTaskId),
    refetchInterval: activeTaskId ? 1200 : undefined,
  });

  useEffect(() => {
    if (!job?.latest_task) {
      return;
    }
    if ((job.latest_task.status === "queued" || job.latest_task.status === "running") && activeTaskId !== job.latest_task.id) {
      setActiveTaskId(job.latest_task.id);
    }
  }, [activeTaskId, job?.latest_task]);

  useEffect(() => {
    const task = taskQuery.data;
    if (!task) {
      return;
    }

    if (task.status === "completed") {
      const completionMessage =
        task.task_type === "score_job"
          ? "Scoring finished and the latest evaluation plus cover letter were refreshed."
          : task.task_type === "generate_cover_letter"
            ? "Cover-letter regeneration finished and the latest draft is ready."
            : "The latest role workflow finished.";
      setWorkflowMessage(completionMessage);
      setActiveTaskId(null);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
    }

    if (task.status === "failed") {
      setWorkflowMessage(
        task.can_retry
          ? `Task failed: ${String(task.error_message || "unknown error")}. You can retry it after checking the profile or role data.`
          : `Task failed: ${String(task.error_message || "unknown error")}`,
      );
      setActiveTaskId(null);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
    }
  }, [jobId, queryClient, taskQuery.data]);

  if (!job) {
    return null;
  }

  const latestTask = taskQuery.data || job.latest_task || null;
  const taskIsActive = latestTask?.status === "queued" || latestTask?.status === "running";

  const form = useForm({
    defaultValues: {
      status: job.current_status,
    },
    onSubmit: async ({ value }) => {
      await updateStatus.mutateAsync(value);
    },
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Job detail"
        title={`${job.role_title || "Untitled role"} · ${job.company || "Unknown company"}`}
        description="Run the AI workflow, review the strongest fit signals, keep the latest letter close, and update the application stage without losing context."
        action={
          <div className="flex flex-wrap gap-3">
            <Link to="/app/jobs" className={buttonClasses("secondary")}>
              Back to pipeline
            </Link>
            <Link to="/app/dashboard" className={buttonClasses("ghost")}>
              Dashboard
            </Link>
          </div>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_360px]">
        <div className="space-y-5">
          <Card className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill status={job.current_status} />
              {job.latest_evaluation ? <ScorePill score={job.latest_evaluation.score} /> : null}
              {latestTask ? <TaskStatePill status={latestTask.status} /> : null}
            </div>
            <div className="grid gap-4 md:grid-cols-4">
              <InfoCard label="Location" value={job.location || "Not set"} />
              <InfoCard label="Source" value={job.source_url || "Not added"} />
              <InfoCard label="Profile link" value={job.profile_id ? "Attached" : "Not attached"} />
              <InfoCard
                label="Last updated"
                value={formatTimestamp(job.updated_at, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[var(--page-ink)]">Description</h2>
              <pre className="mt-3 whitespace-pre-wrap rounded-[24px] bg-stone-100 p-5 text-sm leading-7 text-[var(--page-ink)]">
                {job.description}
              </pre>
            </div>
          </Card>

          <Card className="space-y-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[var(--page-ink)]">Latest evaluation</h2>
                <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
                  The latest score, verdict, and reasoning captured against this exact job snapshot.
                </p>
              </div>
              {job.latest_evaluation ? (
                <div className="flex flex-wrap items-center gap-2">
                  <ScorePill score={job.latest_evaluation.score} />
                  <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-[var(--page-ink)]">
                    {humanizeVerdict(job.latest_evaluation.verdict)}
                  </span>
                </div>
              ) : null}
            </div>
            {job.latest_evaluation ? (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-[24px] border border-[rgba(15,118,110,0.16)] bg-[var(--accent-soft)] p-5">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">Assessment</p>
                    <p className="mt-3 text-sm leading-7 text-[var(--page-ink)]">{job.latest_evaluation.feedback}</p>
                  </div>
                  <div className="grid gap-3">
                    <InfoCard label="Verdict" value={humanizeVerdict(job.latest_evaluation.verdict)} />
                    <InfoCard label="Model" value={job.latest_evaluation.model} />
                    <InfoCard
                      label="Scored"
                      value={formatTimestamp(job.latest_evaluation.created_at, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <ListPanel title="Top strengths" items={job.latest_evaluation.top_strengths} tone="positive" />
                  <ListPanel title="Critical gaps" items={job.latest_evaluation.critical_gaps} tone="warn" />
                </div>
              </div>
            ) : (
              <EmptyState
                title="No evaluation yet"
                description="Run the first evaluation for this role to see fit feedback, strengths, and gaps here."
              />
            )}
          </Card>

          <Card className="space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[var(--page-ink)]">Latest cover letter</h2>
                <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
                  The newest draft produced from the latest evaluation context.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                {job.latest_cover_letter ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={async () => {
                      await navigator.clipboard.writeText(job.latest_cover_letter?.content || "");
                      setCopiedLetter(true);
                      window.setTimeout(() => setCopiedLetter(false), 1800);
                    }}
                  >
                    {copiedLetter ? "Copied" : "Copy letter"}
                  </Button>
                ) : null}
                {job.latest_cover_letter ? (
                  <Link to="/app/letters" className={buttonClasses("secondary")}>
                    Open letter library
                  </Link>
                ) : null}
              </div>
            </div>
            {job.latest_cover_letter ? (
              <>
                <div className="rounded-[26px] border border-[var(--line)] bg-white/80 px-6 py-6">
                  <LetterPreview content={job.latest_cover_letter.content} />
                </div>
                <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">
                  Latest letter updated{" "}
                  {formatTimestamp(job.latest_cover_letter.updated_at, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </>
            ) : (
              <EmptyState
                title="No cover letter yet"
                description="Once the scoring task runs, the latest cover letter will show up here automatically."
              />
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--page-ink)]">AI workflow</h2>
            <p className="text-sm leading-7 text-[var(--muted-ink)]">
              Trigger scoring or refresh the cover letter here. The page will keep polling until the active task settles.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                disabled={scoreJob.isPending || taskIsActive}
                onClick={async () => {
                  const accepted = await scoreJob.mutateAsync();
                  setWorkflowMessage(null);
                  setActiveTaskId(accepted.task_id);
                }}
              >
                {scoreJob.isPending ? "Starting score…" : job.latest_evaluation ? "Re-score job" : "Score this job"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={regenerateCoverLetter.isPending || taskIsActive || !job.latest_evaluation}
                onClick={async () => {
                  const accepted = await regenerateCoverLetter.mutateAsync();
                  setWorkflowMessage(null);
                  setActiveTaskId(accepted.task_id);
                }}
              >
                {regenerateCoverLetter.isPending ? "Queueing…" : "Regenerate cover letter"}
              </Button>
            </div>
            {!job.latest_evaluation ? (
              <p className="text-sm text-[var(--muted-ink)]">Run scoring once before regenerating a cover letter.</p>
            ) : null}
            {scoreJob.error ? <p className="text-sm text-rose-700">{describeApiError(scoreJob.error)}</p> : null}
            {regenerateCoverLetter.error ? <p className="text-sm text-rose-700">{describeApiError(regenerateCoverLetter.error)}</p> : null}
            {retryTask.error ? <p className="text-sm text-rose-700">{describeApiError(retryTask.error)}</p> : null}
            {latestTask ? (
              <TaskSummaryCard task={latestTask} />
            ) : (
              <div className="rounded-[22px] border border-dashed border-[var(--line)] bg-white/75 p-4 text-sm text-[var(--muted-ink)]">
                No task has run for this role yet.
              </div>
            )}
            {latestTask?.status === "failed" && latestTask.can_retry ? (
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={retryTask.isPending}
                  onClick={async () => {
                    const accepted = await retryTask.mutateAsync(latestTask.id);
                    setWorkflowMessage("Retry queued. The page will keep polling until it settles.");
                    setActiveTaskId(accepted.task_id);
                  }}
                >
                  {retryTask.isPending ? "Retrying…" : "Retry failed task"}
                </Button>
                <p className="self-center text-sm text-[var(--muted-ink)]">
                  Failed runs keep their error details so you can recover without losing the role context.
                </p>
              </div>
            ) : null}
            {workflowMessage ? <p className="text-sm text-[var(--page-ink)]">{workflowMessage}</p> : null}
          </Card>

          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--page-ink)]">Workspace record</h2>
            <p className="text-sm leading-7 text-[var(--muted-ink)]">
              Everything important for this role already lives inside the app: status history, latest score, and latest saved letter.
            </p>
            <div className="grid gap-3">
              <InfoCard label="Role status" value={humanizeStatus(job.current_status)} />
              <InfoCard label="Saved letter" value={job.latest_cover_letter ? "Available" : "Not generated yet"} />
              <InfoCard label="Latest score" value={job.latest_evaluation ? `${job.latest_evaluation.score}/100` : "Not scored yet"} />
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/app/jobs" className={buttonClasses("secondary")}>
                Open pipeline
              </Link>
              <Link to="/app/letters" className={buttonClasses("ghost")}>
                Open letter library
              </Link>
            </div>
          </Card>

          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--page-ink)]">Update status</h2>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                event.stopPropagation();
                void form.handleSubmit();
              }}
            >
              <form.Field name="status">
                {(field) => (
                  <Field label="Current application stage">
                    <Select value={field.state.value} onChange={(event) => field.handleChange(event.target.value as typeof field.state.value)}>
                      {APPLICATION_STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                          {humanizeStatus(status)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
              </form.Field>
              <Button type="submit" disabled={updateStatus.isPending}>
                {updateStatus.isPending ? "Updating…" : "Save status"}
              </Button>
              {updateStatus.error ? <p className="text-sm text-rose-700">{String(updateStatus.error.message)}</p> : null}
            </form>
          </Card>

          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--page-ink)]">Status history</h2>
            <div className="space-y-3">
              {job.status_history.map((event) => (
                <div key={event.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
                  <p className="font-semibold text-[var(--page-ink)]">{humanizeStatus(event.next_status)}</p>
                  <p className="mt-1 text-sm text-[var(--muted-ink)]">
                    {event.previous_status ? `from ${humanizeStatus(event.previous_status)}` : "initial status"}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">
                    {formatTimestamp(event.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] bg-stone-100 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">{label}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--page-ink)]">{value}</p>
    </div>
  );
}

function ListPanel({ title, items, tone }: { title: string; items: string[]; tone: "positive" | "warn" }) {
  return (
    <div className={`rounded-[22px] p-4 ${tone === "positive" ? "bg-emerald-50" : "bg-amber-50"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">{title}</p>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--page-ink)]">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

function TaskSummaryCard({
  task,
}: {
  task: NonNullable<JobDetailResponse["latest_task"]> | BackgroundTaskResponse;
}) {
  if (!task) {
    return null;
  }

  const tone =
    task.status === "completed"
      ? "border-emerald-200 bg-emerald-50"
      : task.status === "failed"
        ? "border-rose-200 bg-rose-50"
        : "border-[rgba(15,118,110,0.16)] bg-[var(--accent-soft)]";

  const taskResult = "result" in task ? task.result : null;
  const resultScore = "result_score" in task ? task.result_score : typeof taskResult?.score === "number" ? taskResult.score : null;
  const resultVerdict =
    "result_verdict" in task ? task.result_verdict : typeof taskResult?.verdict === "string" ? taskResult.verdict : null;

  return (
    <div className={`rounded-[22px] border p-4 ${tone}`}>
      <div className="flex flex-wrap items-center gap-2">
        <TaskStatePill status={task.status} />
        <span className="text-sm font-semibold text-[var(--page-ink)]">{humanizeTaskType(task.task_type)}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--muted-ink)]">
        Started {formatTimestamp(task.created_at)} · Updated {formatTimestamp(task.updated_at)}
      </p>
      <p className="mt-2 text-sm leading-6 text-[var(--muted-ink)]">
        Attempt {task.attempt_count} of {task.max_attempts}
        {task.next_retry_at ? ` · next retry ${formatTimestamp(task.next_retry_at)}` : ""}
      </p>
      {task.status === "completed" && resultScore !== null && resultScore !== undefined ? (
        <p className="mt-2 text-sm leading-6 text-[var(--page-ink)]">
          Latest result: {resultScore}/100{resultVerdict ? ` · ${humanizeVerdict(resultVerdict)}` : ""}.
        </p>
      ) : null}
      {task.error_message ? <p className="mt-2 text-sm leading-6 text-rose-700">{task.error_message}</p> : null}
      {"id" in task ? <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">Task id · {task.id}</p> : null}
    </div>
  );
}

function TaskStatePill({ status }: { status: string }) {
  const tone =
    status === "completed"
      ? "bg-emerald-100 text-emerald-800"
      : status === "failed"
        ? "bg-rose-100 text-rose-700"
        : status === "running"
          ? "bg-teal-100 text-teal-800"
          : "bg-stone-100 text-stone-700";
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>{status}</span>;
}

function LetterPreview({ content }: { content: string }) {
  return (
    <div className="space-y-5">
      {content.split(/\n{2,}/).map((paragraph, index) => (
        <p key={`${index}-${paragraph.slice(0, 20)}`} className="whitespace-pre-wrap text-sm leading-7 text-[var(--page-ink)]">
          {paragraph.trim()}
        </p>
      ))}
    </div>
  );
}
