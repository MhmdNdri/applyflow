import { ClerkProvider } from "@clerk/clerk-react";

import { appConfig } from "@/lib/config";
import { MissingConfigPage } from "@/pages/missing-config-page";

import { AppProviders } from "./providers";

export function App() {
  if (!appConfig.clerkPublishableKey) {
    return <MissingConfigPage />;
  }

  return (
    <ClerkProvider publishableKey={appConfig.clerkPublishableKey} afterSignOutUrl="/">
      <AppProviders />
    </ClerkProvider>
  );
}
