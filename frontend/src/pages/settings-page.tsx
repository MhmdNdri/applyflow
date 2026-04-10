import { Card, PageHeader } from "@/components/ui";
import { appConfig } from "@/lib/config";

export function SettingsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Settings"
        title="Environment and workspace posture"
        description="This view keeps the current browser setup visible without making the product feel like a developer demo."
        backTo="/app/dashboard"
        backLabel="Back to dashboard"
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="text-xl font-semibold text-[var(--page-ink)]">Frontend configuration</h2>
          <dl className="space-y-3 text-sm leading-7 text-[var(--page-ink)]">
            <div>
              <dt className="font-semibold text-[var(--muted-ink)]">API base URL</dt>
              <dd>{appConfig.apiBaseUrl}</dd>
            </div>
            <div>
              <dt className="font-semibold text-[var(--muted-ink)]">Clerk publishable key</dt>
              <dd>{appConfig.clerkPublishableKey ? "Configured" : "Missing"}</dd>
            </div>
          </dl>
        </Card>
        <Card className="space-y-3">
          <h2 className="text-xl font-semibold text-[var(--page-ink)]">What is still intentionally deferred</h2>
          <ul className="space-y-2 text-sm leading-7 text-[var(--muted-ink)]">
            <li>• Richer reminders, follow-up nudges, and timeline notes around each role</li>
            <li>• External exports beyond the internal tracker and internal letter library</li>
            <li>• Websocket updates or external worker status streams</li>
            <li>• Billing, scraping, and team features</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
