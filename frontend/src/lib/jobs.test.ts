import { describe, expect, it } from "vitest";

import type { JobListItemResponse } from "./api/types";
import {
  buildDashboardActions,
  buildDashboardMetrics,
  buildJobWorkflowSummary,
  findActiveWorkflowJobs,
  findBestFitJob,
  humanizeStatus,
  humanizeVerdict,
} from "./jobs";

describe("jobs helpers", () => {
  const jobs: JobListItemResponse[] = [
    {
      id: "1",
      profile_id: "p1",
      company: "Lendable",
      role_title: "Senior React Engineer",
      location: "London",
      source_url: null,
      current_status: "waiting",
      latest_evaluation: null,
      latest_task: {
        id: "t1",
        task_type: "score_job",
        status: "running",
        error_message: null,
        result_score: null,
        result_verdict: null,
        attempt_count: 1,
        max_attempts: 3,
        can_retry: false,
        created_at: "2026-03-29T10:00:00Z",
        updated_at: "2026-03-29T10:05:00Z",
        last_attempt_at: "2026-03-29T10:00:00Z",
        next_retry_at: null,
        completed_at: null,
      },
      created_at: "2026-03-29T10:00:00Z",
      updated_at: "2026-03-29T10:05:00Z",
    },
    {
      id: "2",
      profile_id: "p1",
      company: "Growe",
      role_title: "Frontend Lead",
      location: "Remote",
      source_url: null,
      current_status: "interviewing",
      latest_evaluation: {
        id: "e1",
        score: 91,
        verdict: "strong_fit",
        top_strengths: ["React"],
        critical_gaps: ["None"],
        feedback: "Strong fit.",
        model: "gpt-5.4-mini",
        created_at: "2026-03-29T10:00:00Z",
      },
      latest_task: {
        id: "t2",
        task_type: "score_job",
        status: "completed",
        error_message: null,
        result_score: 91,
        result_verdict: "strong_fit",
        attempt_count: 1,
        max_attempts: 3,
        can_retry: false,
        created_at: "2026-03-29T10:00:00Z",
        updated_at: "2026-03-29T10:10:00Z",
        last_attempt_at: "2026-03-29T10:00:00Z",
        next_retry_at: null,
        completed_at: "2026-03-29T10:10:00Z",
      },
      created_at: "2026-03-29T10:00:00Z",
      updated_at: "2026-03-29T10:10:00Z",
    },
    {
      id: "3",
      profile_id: "p1",
      company: "Acme",
      role_title: "Staff Engineer",
      location: "Remote",
      source_url: null,
      current_status: "offer",
      latest_evaluation: {
        id: "e2",
        score: 84,
        verdict: "possible_fit",
        top_strengths: ["Delivery"],
        critical_gaps: ["Domain"],
        feedback: "Solid fit.",
        model: "gpt-5.4-mini",
        created_at: "2026-03-29T10:00:00Z",
      },
      latest_task: {
        id: "t3",
        task_type: "generate_cover_letter",
        status: "failed",
        error_message: "Timeout",
        result_score: null,
        result_verdict: null,
        attempt_count: 2,
        max_attempts: 2,
        can_retry: true,
        created_at: "2026-03-29T10:00:00Z",
        updated_at: "2026-03-29T10:15:00Z",
        last_attempt_at: "2026-03-29T10:14:00Z",
        next_retry_at: null,
        completed_at: null,
      },
      created_at: "2026-03-29T10:00:00Z",
      updated_at: "2026-03-29T10:15:00Z",
    },
  ];

  it("builds richer dashboard totals from job rows", () => {
    const metrics = buildDashboardMetrics(jobs);

    expect(metrics).toEqual({
      total: 3,
      interviewing: 1,
      offers: 1,
      waiting: 1,
      scored: 2,
      needsScoring: 1,
      activeTasks: 1,
    });
  });

  it("humanizes application statuses and verdicts", () => {
    expect(humanizeStatus("recruiter screen")).toBe("Recruiter Screen");
    expect(humanizeVerdict("strong_fit")).toBe("Strong Fit");
  });

  it("suggests practical next actions from job data", () => {
    const actions = buildDashboardActions(jobs);

    expect(actions).toHaveLength(3);
    expect(actions[0]?.title).toContain("active AI");
  });

  it("finds the best fit job", () => {
    const best = findBestFitJob(jobs);
    expect(best?.id).toBe("2");
  });

  it("finds workflow-active or failed jobs", () => {
    const active = findActiveWorkflowJobs(jobs);
    expect(active.map((job) => job.id)).toEqual(["1", "3"]);
  });

  it("builds a readable workflow summary", () => {
    expect(buildJobWorkflowSummary(jobs[0])).toContain("running");
    expect(buildJobWorkflowSummary(jobs[1])).toContain("91/100");
  });
});
