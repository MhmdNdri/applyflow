import { useAuth } from "@clerk/clerk-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClient, ApiError } from "./client";
import type { JobCreateRequest, JobStatusUpdateRequest, JobUpdateRequest, ProfileCreateRequest, ProfileUpdateRequest } from "./types";

function createQueryKey(...segments: Array<string | undefined>) {
  return segments.filter(Boolean);
}

export function useApiClient() {
  const { getToken } = useAuth();
  return new ApiClient(() => getToken());
}

export function useAuthMeQuery(options?: { enabled?: boolean }) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => client.getMe(),
    enabled: options?.enabled,
    retry: false,
  });
}

export function useCoverLettersQuery(options?: { enabled?: boolean }) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["cover-letters"],
    queryFn: () => client.listCoverLetters(),
    enabled: options?.enabled,
    retry: false,
  });
}

export function useProfileQuery(options?: { enabled?: boolean }) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => client.getProfile(),
    enabled: options?.enabled,
    retry: false,
  });
}

export function useJobsQuery(options?: { enabled?: boolean }) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => client.listJobs(),
    enabled: options?.enabled,
    retry: false,
  });
}

export function useJobDetailQuery(jobId: string, options?: { enabled?: boolean }) {
  const client = useApiClient();
  return useQuery({
    queryKey: createQueryKey("jobs", jobId),
    queryFn: () => client.getJob(jobId),
    enabled: options?.enabled ?? Boolean(jobId),
    retry: false,
  });
}

export function useTaskQuery(taskId: string, options?: { enabled?: boolean; refetchInterval?: number }) {
  const client = useApiClient();
  return useQuery({
    queryKey: createQueryKey("tasks", taskId),
    queryFn: () => client.getTask(taskId),
    enabled: options?.enabled ?? Boolean(taskId),
    retry: false,
    refetchInterval: options?.refetchInterval,
  });
}

export function useCreateProfileMutation() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileCreateRequest) => client.createProfile(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}

export function useUpdateProfileMutation() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileUpdateRequest) => client.updateProfile(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}

export function useCreateJobMutation() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobCreateRequest) => client.createJob(payload),
    onSuccess: async (job) => {
      queryClient.setQueryData(createQueryKey("jobs", job.id), job);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["profile"] }),
      ]);
    },
  });
}

export function useUpdateJobMutation(jobId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobUpdateRequest) => client.updateJob(jobId, payload),
    onSuccess: async (job) => {
      queryClient.setQueryData(createQueryKey("jobs", job.id), job);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useUpdateJobStatusMutation(jobId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobStatusUpdateRequest) => client.updateJobStatus(jobId, payload),
    onSuccess: async (job) => {
      queryClient.setQueryData(createQueryKey("jobs", job.id), job);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useScoreJobMutation(jobId: string) {
  const client = useApiClient();
  return useMutation({
    mutationFn: () => client.scoreJob(jobId),
  });
}

export function useRegenerateCoverLetterMutation(jobId: string) {
  const client = useApiClient();
  return useMutation({
    mutationFn: () => client.regenerateCoverLetter(jobId),
  });
}

export function useRetryTaskMutation() {
  const client = useApiClient();
  return useMutation({
    mutationFn: (taskId: string) => client.retryTask(taskId),
  });
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof ApiError && (status === undefined || error.status === status);
}
