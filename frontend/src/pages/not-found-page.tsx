import { Link } from "@tanstack/react-router";

import { Card, buttonClasses } from "@/components/ui";

export function NotFoundPage() {
  return (
    <div className="page-shell flex items-center justify-center px-4 py-10">
      <Card className="max-w-xl space-y-4 p-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--accent)]">404</p>
        <h1 className="hero-title text-4xl text-[var(--page-ink)]">This route does not exist yet</h1>
        <p className="text-base leading-7 text-[var(--muted-ink)]">
          The frontend shell is still growing phase by phase, so some routes are intentionally not implemented yet.
        </p>
        <div>
          <Link to="/" className={buttonClasses("primary")}>
            Return home
          </Link>
        </div>
      </Card>
    </div>
  );
}
