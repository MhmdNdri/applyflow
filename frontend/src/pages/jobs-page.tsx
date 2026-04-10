import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, ChevronDown, ChevronUp } from "lucide-react";
import { startTransition, useDeferredValue, useState } from "react";

import { Button, Card, EmptyState, Field, LoadingState, PageHeader, ScorePill, Select, StatusPill, TextArea, TextInput } from "@/components/ui";
import { describeApiError } from "@/lib/api/client";
import { useCreateJobMutation, useJobsQuery } from "@/lib/api/hooks";
import type { JobListItemResponse } from "@/lib/api/types";
import { APPLICATION_STATUS_OPTIONS, buildJobWorkflowSummary, formatTimestamp, humanizeStatus, humanizeTaskType } from "@/lib/jobs";

const columnHelper = createColumnHelper<JobListItemResponse>();

const COLUMNS = [
  columnHelper.accessor("role_title", {
    header: "Role",
    enableSorting: true,
    cell: (info) => (
      <div className="space-y-0.5 min-w-[140px]">
        <p className="font-semibold text-[var(--page-ink)] leading-snug">{info.getValue() || "Untitled role"}</p>
        <p className="text-xs text-[var(--muted-ink)]">{info.row.original.company || "Unknown company"}</p>
      </div>
    ),
  }),
  columnHelper.accessor("location", {
    header: "Location",
    enableSorting: true,
    cell: (info) => <span className="text-sm text-[var(--muted-ink)] whitespace-nowrap">{info.getValue() || "—"}</span>,
  }),
  columnHelper.display({
    id: "score",
    header: "Score",
    cell: (info) =>
      info.row.original.latest_evaluation ? (
        <ScorePill score={info.row.original.latest_evaluation.score} />
      ) : (
        <span className="text-sm text-[var(--muted-ink)]">—</span>
      ),
  }),
  columnHelper.accessor("current_status", {
    header: "Status",
    enableSorting: true,
    cell: (info) => <StatusPill status={info.getValue()} />,
  }),
  columnHelper.display({
    id: "letter",
    header: "Letter",
    cell: (info) =>
      info.row.original.latest_cover_letter ? (
        <div className="space-y-0.5 min-w-[110px]">
          <p className="text-sm font-medium text-[var(--page-ink)]">Saved</p>
          <p className="text-xs text-[var(--muted-ink)]">{formatTimestamp(info.row.original.latest_cover_letter.updated_at)}</p>
        </div>
      ) : (
        <span className="text-sm text-[var(--muted-ink)] whitespace-nowrap">No letter yet</span>
      ),
  }),
  columnHelper.display({
    id: "workflow_state",
    header: "Workflow",
    cell: (info) => (
      <div className="space-y-0.5 min-w-[120px]">
        <p className="text-sm text-[var(--page-ink)]">{buildJobWorkflowSummary(info.row.original)}</p>
        {info.row.original.latest_task ? (
          <p className="text-xs text-[var(--muted-ink)]">
            {humanizeTaskType(info.row.original.latest_task.task_type)} · {formatTimestamp(info.row.original.latest_task.updated_at)}
          </p>
        ) : null}
      </div>
    ),
  }),
  columnHelper.display({
    id: "open",
    header: "",
    cell: (info) => (
      <Link
        to="/app/jobs/$jobId"
        params={{ jobId: info.row.original.id }}
        className="inline-flex items-center gap-1 rounded-full border border-[var(--accent)] px-3 py-1 text-xs font-semibold text-[var(--accent)] transition hover:bg-[var(--accent)] hover:text-white"
        onClick={(e) => e.stopPropagation()}
      >
        Open
      </Link>
    ),
  }),
];

export function JobsPage() {
  const jobsQuery = useJobsQuery({ enabled: true });
  const createJob = useCreateJobMutation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | (typeof APPLICATION_STATUS_OPTIONS)[number]>("all");
  const [sorting, setSorting] = useState<SortingState>([]);
  const deferredSearch = useDeferredValue(search);

  const form = useForm({
    defaultValues: {
      company: "",
      role_title: "",
      location: "",
      source_url: "",
      description: "",
      current_status: "waiting" as const,
    },
    onSubmit: async ({ value }) => {
      const created = await createJob.mutateAsync({
        ...value,
        source_url: value.source_url || null,
        company: value.company || null,
        role_title: value.role_title || null,
        location: value.location || null,
      });
      startTransition(() => {
        void navigate({ to: "/app/jobs/$jobId", params: { jobId: created.id } });
      });
    },
  });

  const allRows = jobsQuery.data ?? [];
  const rows = allRows.filter((job) => {
    const haystack = `${job.company || ""} ${job.role_title || ""} ${job.location || ""}`.toLowerCase();
    const matchesSearch = deferredSearch.trim() ? haystack.includes(deferredSearch.trim().toLowerCase()) : true;
    const matchesStatus = statusFilter === "all" ? true : job.current_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const table = useReactTable({
    data: rows,
    columns: COLUMNS,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (jobsQuery.isPending) {
    return <LoadingState title="Loading pipeline" description="Opening the latest roles, statuses, scores, and saved letters." />;
  }

  if (jobsQuery.isError) {
    return (
      <EmptyState
        title="Jobs could not load"
        description={`The API returned an error while loading your jobs: ${describeApiError(jobsQuery.error)}`}
      />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Pipeline"
        title="Your internal application tracker"
        description="Use this built-in table like your private spreadsheet: roles, status, score, and saved letters all stay in one database-backed view."
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Card className="min-w-0 space-y-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-[var(--page-ink)]">Role table</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
                Filter by text or stage, then jump straight into the role. Click a column header to sort.
              </p>
            </div>
            <div className="flex shrink-0 flex-col gap-3 sm:flex-row">
              <TextInput value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search company or role" className="sm:w-52" />
              <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)} className="sm:w-44">
                <option value="all">All statuses</option>
                {APPLICATION_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {humanizeStatus(status)}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {rows.length === 0 ? (
            <EmptyState title="No roles match your filters" description="Adjust the search or create a fresh role in the form beside this table." />
          ) : (
            <>
              <div className="w-full overflow-x-auto rounded-[20px] border border-[var(--line)]">
                <table className="w-full min-w-[680px] border-collapse text-sm">
                  <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                      <tr key={headerGroup.id} className="border-b border-[var(--line)] bg-stone-50/80">
                        {headerGroup.headers.map((header) => {
                          const canSort = header.column.getCanSort();
                          const sorted = header.column.getIsSorted();
                          return (
                            <th
                              key={header.id}
                              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted-ink)]"
                            >
                              {header.isPlaceholder ? null : canSort ? (
                                <button
                                  type="button"
                                  onClick={header.column.getToggleSortingHandler()}
                                  className="inline-flex cursor-pointer items-center gap-1.5 transition-colors hover:text-[var(--page-ink)]"
                                >
                                  {flexRender(header.column.columnDef.header, header.getContext())}
                                  {sorted === "asc" ? (
                                    <ChevronUp className="h-3 w-3 text-[var(--accent)]" />
                                  ) : sorted === "desc" ? (
                                    <ChevronDown className="h-3 w-3 text-[var(--accent)]" />
                                  ) : (
                                    <ArrowUpDown className="h-3 w-3 opacity-40" />
                                  )}
                                </button>
                              ) : (
                                flexRender(header.column.columnDef.header, header.getContext())
                              )}
                            </th>
                          );
                        })}
                      </tr>
                    ))}
                  </thead>
                  <tbody className="divide-y divide-[var(--line)] bg-white/60">
                    {table.getRowModel().rows.map((row) => (
                      <tr
                        key={row.id}
                        className="group cursor-pointer transition-colors hover:bg-[var(--accent-soft)]/40"
                        onClick={() => {
                          void navigate({ to: "/app/jobs/$jobId", params: { jobId: row.original.id } });
                        }}
                      >
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="px-4 py-3.5 align-middle">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-[var(--muted-ink)]">
                {rows.length === allRows.length
                  ? `${allRows.length} role${allRows.length === 1 ? "" : "s"}`
                  : `${rows.length} of ${allRows.length} roles`}
              </p>
            </>
          )}
        </Card>

        <Card className="space-y-5">
          <div>
            <h2 className="text-xl font-semibold text-[var(--page-ink)]">Add a job</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--muted-ink)]">
              Create the role record here, then use the detail page to run scoring, regenerate the letter, and keep the latest state in one place.
            </p>
          </div>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void form.handleSubmit();
            }}
          >
            <form.Field name="company">
              {(field) => (
                <Field label="Company">
                  <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                </Field>
              )}
            </form.Field>
            <form.Field name="role_title">
              {(field) => (
                <Field label="Role title">
                  <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                </Field>
              )}
            </form.Field>
            <div className="grid gap-4 md:grid-cols-2">
              <form.Field name="location">
                {(field) => (
                  <Field label="Location">
                    <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                  </Field>
                )}
              </form.Field>
              <form.Field name="current_status">
                {(field) => (
                  <Field label="Initial status">
                    <Select value={field.state.value} onChange={(event) => field.handleChange(event.target.value as typeof field.state.value)}>
                      {APPLICATION_STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                          {humanizeStatus(status)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
              </form.Field>
            </div>
            <form.Field name="source_url">
              {(field) => (
                <Field label="Source URL">
                  <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} placeholder="https://..." />
                </Field>
              )}
            </form.Field>
            <form.Field name="description">
              {(field) => (
                <Field label="Job description" hint="Paste the real role text here. Once saved, the detail page can score it and generate the latest letter.">
                  <TextArea value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                </Field>
              )}
            </form.Field>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={createJob.isPending}>
                {createJob.isPending ? "Creating…" : "Create job"}
              </Button>
              {createJob.error ? <p className="text-sm text-rose-700">{describeApiError(createJob.error)}</p> : null}
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
