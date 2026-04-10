import { appConfig } from "@/lib/config";

import type {
  AuthMeResponse,
  BackgroundTaskResponse,
  CoverLetterListItemResponse,
  JobCreateRequest,
  JobDetailResponse,
  JobListItemResponse,
  JobStatusUpdateRequest,
  JobUpdateRequest,
  ProfileCreateRequest,
  ProfileResponse,
  ProfileUpdateRequest,
  TaskAcceptedResponse,
} from "./types";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API request failed with status ${status}.`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    if (Array.isArray(error.detail)) {
      return error.detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join(" • ");
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown API error.";
}

type AccessTokenProvider = () => Promise<string | null>;

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getAccessToken: AccessTokenProvider;

  constructor(getAccessToken: AccessTokenProvider, baseUrl = appConfig.apiBaseUrl) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.getAccessToken = getAccessToken;
  }

  async getMe(): Promise<AuthMeResponse> {
    return this.request<AuthMeResponse>("/auth/me");
  }

  async getProfile(): Promise<ProfileResponse> {
    return this.request<ProfileResponse>("/profile");
  }

  async createProfile(payload: ProfileCreateRequest): Promise<ProfileResponse> {
    return this.request<ProfileResponse>("/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async updateProfile(payload: ProfileUpdateRequest): Promise<ProfileResponse> {
    return this.request<ProfileResponse>("/profile", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async listJobs(): Promise<JobListItemResponse[]> {
    return this.request<JobListItemResponse[]>("/jobs");
  }

  async listCoverLetters(): Promise<CoverLetterListItemResponse[]> {
    return this.request<CoverLetterListItemResponse[]>("/cover-letters");
  }

  async createJob(payload: JobCreateRequest): Promise<JobDetailResponse> {
    return this.request<JobDetailResponse>("/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getJob(jobId: string): Promise<JobDetailResponse> {
    return this.request<JobDetailResponse>(`/jobs/${jobId}`);
  }

  async updateJob(jobId: string, payload: JobUpdateRequest): Promise<JobDetailResponse> {
    return this.request<JobDetailResponse>(`/jobs/${jobId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async updateJobStatus(jobId: string, payload: JobStatusUpdateRequest): Promise<JobDetailResponse> {
    return this.request<JobDetailResponse>(`/jobs/${jobId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async scoreJob(jobId: string): Promise<TaskAcceptedResponse> {
    return this.request<TaskAcceptedResponse>(`/jobs/${jobId}/score`, {
      method: "POST",
    });
  }

  async regenerateCoverLetter(jobId: string): Promise<TaskAcceptedResponse> {
    return this.request<TaskAcceptedResponse>(`/jobs/${jobId}/cover-letter/regenerate`, {
      method: "POST",
    });
  }

  async getTask(taskId: string): Promise<BackgroundTaskResponse> {
    return this.request<BackgroundTaskResponse>(`/tasks/${taskId}`);
  }

  async retryTask(taskId: string): Promise<TaskAcceptedResponse> {
    return this.request<TaskAcceptedResponse>(`/tasks/${taskId}/retry`, {
      method: "POST",
    });
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await this.getAccessToken();
    if (!token) {
      throw new ApiError(401, "Missing Clerk session token.");
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init.headers || {}),
      },
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? ((await response.json()) as unknown)
      : await response.text();

    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? (payload as { detail: unknown }).detail
          : payload;
      throw new ApiError(response.status, detail);
    }

    return payload as T;
  }
}
