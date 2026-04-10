import { Navigate, Outlet, createRootRoute, createRoute, createRouter } from "@tanstack/react-router";

import { DashboardPage } from "@/pages/dashboard-page";
import { JobDetailPage } from "@/pages/job-detail-page";
import { JobsPage } from "@/pages/jobs-page";
import { LandingPage } from "@/pages/landing-page";
import { LettersPage } from "@/pages/letters-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { OnboardingPage } from "@/pages/onboarding-page";
import { ProfilePage } from "@/pages/profile-page";
import { SettingsPage } from "@/pages/settings-page";

import { AppShell } from "@/components/app-shell";

function RootComponent() {
  return <Outlet />;
}

const rootRoute = createRootRoute({
  component: RootComponent,
  notFoundComponent: NotFoundPage,
});

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: LandingPage,
});

const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app",
  component: () => <Outlet />,
});

const appIndexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  component: () => <Navigate to="/app/dashboard" />,
});

const dashboardRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/dashboard",
  component: () => (
    <AppShell title="Dashboard" description="A clear overview of your current application momentum.">
      <DashboardPage />
    </AppShell>
  ),
});

const onboardingRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/onboarding",
  component: () => (
    <AppShell
      allowMissingProfile
      title="Onboarding"
      description="Create the profile snapshot the API will attach to your future jobs."
    >
      <OnboardingPage />
    </AppShell>
  ),
});

const jobsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/jobs",
  component: () => (
    <AppShell title="Pipeline" description="Track the roles, scores, letters, and stage changes that make up your internal application tracker.">
      <JobsPage />
    </AppShell>
  ),
});

const lettersRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/letters",
  component: () => (
    <AppShell title="Letters" description="Review, copy, and manage your saved cover letters directly inside the workspace.">
      <LettersPage />
    </AppShell>
  ),
});

const jobDetailRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/jobs/$jobId",
  component: () => (
    <AppShell title="Job detail" description="Follow one role through its evolving application record.">
      <JobDetailPage />
    </AppShell>
  ),
});

const profileRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/profile",
  component: () => (
    <AppShell title="Profile" description="Update the database-backed resume and context snapshot for future runs.">
      <ProfilePage />
    </AppShell>
  ),
});

const settingsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/settings",
  component: () => (
    <AppShell title="Settings" description="Environment and rollout context for the frontend shell.">
      <SettingsPage />
    </AppShell>
  ),
});

const routeTree = rootRoute.addChildren([
  landingRoute,
  appRoute.addChildren([
    appIndexRoute,
    dashboardRoute,
    onboardingRoute,
    jobsRoute,
    lettersRoute,
    jobDetailRoute,
    profileRoute,
    settingsRoute,
  ]),
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
