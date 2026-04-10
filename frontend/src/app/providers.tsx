import { useAuth } from "@clerk/clerk-react";
import type { ReactNode } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";

import { LoadingState } from "@/components/ui";

import { router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

export function AppProviders({ children }: { children?: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <AuthReadyGate>
        <RouterProvider router={router} />
      </AuthReadyGate>
    </QueryClientProvider>
  );
}

function AuthReadyGate({ children }: { children: ReactNode }) {
  const { isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <div className="page-shell flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-lg">
          <LoadingState
            title="Opening Applyflow"
            description="Restoring your session before we choose the right workspace view."
          />
        </div>
      </div>
    );
  }

  return children;
}
