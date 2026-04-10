import { Button, Field, TextArea } from "@/components/ui";
import { formatBytes, type UploadedProfileDocumentPayload } from "@/lib/uploads";

type StoredSourceFile = {
  file_name: string;
  content_type?: string | null;
  size_bytes: number;
} | null;

export function ProfileDocumentField({
  label,
  hint,
  value,
  onTextChange,
  onFileSelected,
  onClearSelectedFile,
  pendingFileName,
  pendingFileSize,
  savedFile,
}: {
  label: string;
  hint: string;
  value: string;
  onTextChange: (value: string) => void;
  onFileSelected: (file: File | null) => void;
  onClearSelectedFile: () => void;
  pendingFileName: string | null;
  pendingFileSize: number | null;
  savedFile: StoredSourceFile;
}) {
  return (
    <div className="space-y-3">
      <Field label={label} hint={hint}>
        <TextArea value={value} onChange={(event) => onTextChange(event.target.value)} />
      </Field>

      <div className="rounded-[22px] border border-dashed border-[var(--line)] bg-white/70 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-[var(--page-ink)]">Upload PDF, DOCX, TXT, or Markdown</p>
            <p className="text-xs leading-6 text-[var(--muted-ink)]">
              The backend stores the file metadata in the database and extracts readable text for future evaluations.
            </p>
          </div>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,.markdown,.rst,.json,.csv,.yaml,.yml"
            className="block max-w-full text-sm text-[var(--muted-ink)] file:mr-4 file:rounded-full file:border-0 file:bg-[var(--accent-soft)] file:px-4 file:py-2 file:font-semibold file:text-[var(--accent)]"
            onChange={(event) => onFileSelected(event.target.files?.[0] || null)}
          />
        </div>

        <div className="mt-3 space-y-2">
          {pendingFileName ? (
            <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--accent-soft)] px-4 py-3 text-sm text-[var(--page-ink)]">
              <span className="font-semibold">Ready to upload:</span>
              <span>{pendingFileName}</span>
              {pendingFileSize !== null ? <span className="text-[var(--muted-ink)]">{formatBytes(pendingFileSize)}</span> : null}
              <Button type="button" variant="ghost" className="px-0 py-0 text-[var(--accent)]" onClick={onClearSelectedFile}>
                Clear
              </Button>
            </div>
          ) : null}

          {!pendingFileName && savedFile ? (
            <div className="rounded-2xl bg-stone-100 px-4 py-3 text-sm text-[var(--page-ink)]">
              <span className="font-semibold">Latest saved file:</span> {savedFile.file_name}
              <span className="ml-2 text-[var(--muted-ink)]">{formatBytes(savedFile.size_bytes)}</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export type ProfileDocumentUploadState = UploadedProfileDocumentPayload | null;
