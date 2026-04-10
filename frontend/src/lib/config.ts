export const appConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1",
  clerkPublishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "",
} as const;
