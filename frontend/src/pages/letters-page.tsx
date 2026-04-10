import { Link } from "@tanstack/react-router";

import { Card, EmptyState, LoadingState, PageHeader, ScorePill, StatusPill, buttonClasses } from "@/components/ui";
import { describeApiError } from "@/lib/api/client";
import { useCoverLettersQuery } from "@/lib/api/hooks";
import { formatTimestamp } from "@/lib/jobs";

export function LettersPage() {
  const lettersQuery = useCoverLettersQuery({ enabled: true });

  if (lettersQuery.isPending) {
    return <LoadingState title="Loading letters" description="Gathering your generated cover letters and their linked roles." />;
  }

  if (lettersQuery.isError) {
    return (
      <EmptyState
        title="Letters could not load"
        description={`The API returned an error while loading your saved letters: ${describeApiError(lettersQuery.error)}`}
      />
    );
  }

  const letters = lettersQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Letters"
        title="Internal cover-letter library"
        description="Every generated letter lives here inside the workspace, tied to its role, score, and current application stage."
        backTo="/app/dashboard"
        backLabel="Back to dashboard"
        action={
          <div className="flex flex-wrap gap-3">
            <Link to="/app/jobs" className={buttonClasses("secondary")}>
              Open pipeline
            </Link>
            <Link to="/app/dashboard" className={buttonClasses("ghost")}>
              Dashboard
            </Link>
          </div>
        }
      />

      {letters.length === 0 ? (
        <EmptyState
          title="No saved letters yet"
          description="Run scoring on a job first. Each generated cover letter will then appear here automatically."
          action={
            <Link to="/app/jobs" className={buttonClasses("primary")}>
              Open pipeline
            </Link>
          }
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {letters.map((letter) => (
            <Card key={letter.id} className="space-y-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="space-y-1">
                  <p className="text-lg font-semibold text-[var(--page-ink)]">
                    {letter.role_title || "Untitled role"} · {letter.company || "Unknown company"}
                  </p>
                  <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted-ink)]">
                    Updated {formatTimestamp(letter.updated_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={letter.current_status} />
                  {letter.score !== null && letter.score !== undefined ? <ScorePill score={letter.score} /> : null}
                </div>
              </div>

              <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-5">
                <LetterExcerpt content={letter.content} />
              </div>

              <div className="flex flex-wrap gap-3">
                <Link to="/app/jobs/$jobId" params={{ jobId: letter.job_id }} className={buttonClasses("secondary")}>
                  Open role
                </Link>
                <button
                  type="button"
                  className={buttonClasses("ghost")}
                  onClick={async () => {
                    await navigator.clipboard.writeText(letter.content);
                  }}
                >
                  Copy letter
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function LetterExcerpt({ content }: { content: string }) {
  const trimmed = content.trim();
  const paragraphs = trimmed.split(/\n{2,}/).slice(0, 3);

  return (
    <div className="space-y-4">
      {paragraphs.map((paragraph, index) => (
        <p key={`${index}-${paragraph.slice(0, 16)}`} className="whitespace-pre-wrap text-sm leading-7 text-[var(--page-ink)]">
          {paragraph.trim()}
        </p>
      ))}
    </div>
  );
}
