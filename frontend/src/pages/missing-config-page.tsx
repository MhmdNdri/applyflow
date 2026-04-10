import { Card } from "@/components/ui";
import { appConfig } from "@/lib/config";

export function MissingConfigPage() {
  return (
    <div className="page-shell flex items-center justify-center px-4 py-10">
      <Card className="max-w-3xl space-y-4 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">Frontend setup needed</p>
        <h1 className="hero-title text-4xl text-[var(--page-ink)]">Add your Clerk key to launch Applyflow</h1>
        <p className="text-base leading-7 text-[var(--muted-ink)]">
          The frontend shell is in place, but it needs a real Clerk publishable key before it can mount the authenticated application routes.
        </p>
        <div className="rounded-[24px] border border-[var(--line)] bg-white/80 p-5 text-sm leading-7 text-[var(--page-ink)]">
          <p>
            Create <code className="rounded bg-stone-100 px-2 py-1">frontend/.env</code> with:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-2xl bg-stone-950 px-4 py-4 text-sm text-stone-100">
{`VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_API_BASE_URL=${appConfig.apiBaseUrl}`}
          </pre>
        </div>
      </Card>
    </div>
  );
}
