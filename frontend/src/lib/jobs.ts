import type { ApplicationStatus, JobListItemResponse } from "./api/types";

export const APPLICATION_STATUS_OPTIONS: ApplicationStatus[] = [
  "wishlist",
  "applied",
  "waiting",
  "recruiter screen",
  "interview scheduled",
  "interviewing",
  "final round",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
];

export function humanizeStatus(status: ApplicationStatus): string {
  return status.replace(/\b\w/g, (char) => char.toUpperCase());
}

export function humanizeVerdict(verdict: string): string {
  return verdict
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function humanizeTaskType(taskType: string): string {
  return String(taskType)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatTimestamp(value: string | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString(undefined, options);
}

export function buildDashboardMetrics(jobs: JobListItemResponse[]) {
  const scored = jobs.filter((job) => Boolean(job.latest_evaluation)).length;
  const activeTasks = jobs.filter((job) => {
    const status = job.latest_task?.status;
    return status === "queued" || status === "running";
  }).length;
  const needsScoring = jobs.filter((job) => !job.latest_evaluation).length;

  return {
    total: jobs.length,
    interviewing: jobs.filter((job) =>
      ["recruiter screen", "interview scheduled", "interviewing", "final round"].includes(job.current_status),
    ).length,
    offers: jobs.filter((job) => ["offer", "accepted"].includes(job.current_status)).length,
    waiting: jobs.filter((job) => job.current_status === "waiting").length,
    scored,
    needsScoring,
    activeTasks,
  };
}

export function buildDashboardActions(jobs: JobListItemResponse[]) {
  const interviewing = jobs.filter((job) =>
    ["recruiter screen", "interview scheduled", "interviewing", "final round"].includes(job.current_status),
  ).length;
  const waiting = jobs.filter((job) => job.current_status === "waiting").length;
  const wishlist = jobs.filter((job) => job.current_status === "wishlist").length;
  const offers = jobs.filter((job) => ["offer", "accepted"].includes(job.current_status)).length;
  const needsScoring = jobs.filter((job) => !job.latest_evaluation).length;
  const failedTasks = jobs.filter((job) => job.latest_task?.status === "failed").length;
  const activeTasks = jobs.filter((job) => {
    const status = job.latest_task?.status;
    return status === "queued" || status === "running";
  }).length;

  if (jobs.length === 0) {
    return [
      {
        title: "Create your first tracked role",
        description: "Start by saving one real job description so the browser workspace has something concrete to organize.",
      },
      {
        title: "Complete your profile once",
        description: "A strong resume and honest context snapshot make the scoring and cover-letter workflow much more useful.",
      },
      {
        title: "Keep one status language",
        description: "Use the built-in application stages consistently so the dashboard tells the truth about momentum.",
      },
    ];
  }

  const suggestions = [];

  if (activeTasks > 0) {
    suggestions.push({
      title: `Watch ${activeTasks} active AI ${activeTasks === 1 ? "task" : "tasks"}`,
      description: "Recent browser actions are still running. Keep an eye on the detail pages where those results will land.",
    });
  }

  if (failedTasks > 0) {
    suggestions.push({
      title: `Recover ${failedTasks} failed ${failedTasks === 1 ? "workflow" : "workflows"}`,
      description: "A failed score or cover-letter run usually means the job detail page needs another pass or a data fix.",
    });
  }

  if (needsScoring > 0) {
    suggestions.push({
      title: `Score ${needsScoring} ${needsScoring === 1 ? "role" : "roles"} still waiting for signal`,
      description: "Unscored roles are harder to prioritize. Push them through the AI workflow before you lose context.",
    });
  }

  if (waiting > 0) {
    suggestions.push({
      title: `Follow up on ${waiting} waiting ${waiting === 1 ? "role" : "roles"}`,
      description: "Waiting is the easiest state to forget. These are good candidates for follow-up or closure.",
    });
  }

  if (interviewing > 0) {
    suggestions.push({
      title: `Prepare for ${interviewing} active interview ${interviewing === 1 ? "loop" : "loops"}`,
      description: "Keep notes, trade-offs, and next steps close while those conversations are still moving.",
    });
  }

  if (wishlist > 0) {
    suggestions.push({
      title: `Promote ${wishlist} wishlist ${wishlist === 1 ? "role" : "roles"} into action`,
      description: "If a role still matters, move it forward or remove it so the list stays honest.",
    });
  }

  if (offers > 0) {
    suggestions.push({
      title: "Capture offer context clearly",
      description: "Offers and near-offers deserve clean notes on compensation, trade-offs, and timing.",
    });
  }

  suggestions.push({
    title: "Keep the strongest role visible",
    description: "The best-fit score is most useful when it stays tied to the live status and the latest letter, not buried in memory.",
  });

  return suggestions.slice(0, 3);
}

export function findBestFitJob(jobs: JobListItemResponse[]): JobListItemResponse | null {
  const scored = jobs.filter((job) => job.latest_evaluation);
  if (scored.length === 0) {
    return null;
  }
  return [...scored].sort((left, right) => {
    const scoreDiff = (right.latest_evaluation?.score || 0) - (left.latest_evaluation?.score || 0);
    if (scoreDiff !== 0) {
      return scoreDiff;
    }
    return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
  })[0] || null;
}

export function findActiveWorkflowJobs(jobs: JobListItemResponse[]): JobListItemResponse[] {
  return jobs.filter((job) => {
    const status = job.latest_task?.status;
    return status === "queued" || status === "running" || status === "failed";
  });
}

export function buildJobWorkflowSummary(job: JobListItemResponse): string {
  const task = job.latest_task;
  if (task?.status === "running") {
    return `${humanizeTaskType(task.task_type)} is running`;
  }
  if (task?.status === "queued") {
    return `${humanizeTaskType(task.task_type)} is queued`;
  }
  if (task?.status === "failed") {
    return `${humanizeTaskType(task.task_type)} failed`;
  }
  if (job.latest_evaluation) {
    return `${humanizeVerdict(job.latest_evaluation.verdict)} · ${job.latest_evaluation.score}/100`;
  }
  return "Needs first score";
}
