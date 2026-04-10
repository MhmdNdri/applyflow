import { useForm } from "@tanstack/react-form";
import { useState } from "react";

import { ProfileDocumentField } from "@/components/profile-document-field";
import { Button, Card, EmptyState, Field, PageHeader, TextInput } from "@/components/ui";
import { useProfileQuery, useUpdateProfileMutation } from "@/lib/api/hooks";
import { fileToUploadPayload, type UploadedProfileDocumentPayload } from "@/lib/uploads";

export function ProfilePage() {
  const profileQuery = useProfileQuery({ enabled: true });

  if (profileQuery.isPending) {
    return <div className="text-sm text-[var(--muted-ink)]">Loading profile…</div>;
  }

  if (profileQuery.isError || !profileQuery.data) {
    return (
      <EmptyState
        title="Profile unavailable"
        description="The current signed-in user does not have a profile snapshot yet."
      />
    );
  }

  return <ProfileEditor key={profileQuery.data.id} />;
}

function ProfileEditor() {
  const profileQuery = useProfileQuery({ enabled: true });
  const mutation = useUpdateProfileMutation();
  const [resumeUpload, setResumeUpload] = useState<UploadedProfileDocumentPayload | null>(null);
  const [contextUpload, setContextUpload] = useState<UploadedProfileDocumentPayload | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const profile = profileQuery.data;

  if (!profile) {
    return null;
  }

  const form = useForm({
    defaultValues: {
      display_name: profile.display_name || "",
      location: profile.location || "",
      resume_text: profile.resume_text,
      context_text: profile.context_text,
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync({
        ...value,
        resume_upload: resumeUpload,
        context_upload: contextUpload,
      });
      setResumeUpload(null);
      setContextUpload(null);
    },
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Profile"
        title="Keep your core application context sharp"
        description="Updating this page creates fresh resume and context versions in the API-backed database, so future evaluations can use the newest state while old runs stay reproducible."
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="space-y-6">
          <form
            className="space-y-5"
            onSubmit={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void form.handleSubmit();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <form.Field name="display_name">
                {(field) => (
                  <Field label="Full name">
                    <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                  </Field>
                )}
              </form.Field>
              <form.Field name="location">
                {(field) => (
                  <Field label="Location">
                    <TextInput value={field.state.value} onChange={(event) => field.handleChange(event.target.value)} />
                  </Field>
                )}
              </form.Field>
            </div>

            <form.Field name="resume_text">
              {(field) => (
                <ProfileDocumentField
                  label="Resume text"
                  hint="Paste updates directly or upload the latest source file. Uploaded files are stored with the current profile version in the database."
                  value={field.state.value}
                  onTextChange={field.handleChange}
                  onFileSelected={async (file) => {
                    if (!file) {
                      setResumeUpload(null);
                      return;
                    }
                    try {
                      setUploadError(null);
                      setResumeUpload(await fileToUploadPayload(file));
                    } catch (error) {
                      setUploadError(error instanceof Error ? error.message : "The resume file could not be read.");
                    }
                  }}
                  onClearSelectedFile={() => setResumeUpload(null)}
                  pendingFileName={resumeUpload?.file_name || null}
                  pendingFileSize={resumeUpload ? Math.floor((resumeUpload.content_base64.length * 3) / 4) : null}
                  savedFile={profile.resume_source_file ?? null}
                />
              )}
            </form.Field>

            <form.Field name="context_text">
              {(field) => (
                <ProfileDocumentField
                  label="Honest context"
                  hint="Keep the narrative current, either by editing the text directly or uploading a supporting file."
                  value={field.state.value}
                  onTextChange={field.handleChange}
                  onFileSelected={async (file) => {
                    if (!file) {
                      setContextUpload(null);
                      return;
                    }
                    try {
                      setUploadError(null);
                      setContextUpload(await fileToUploadPayload(file));
                    } catch (error) {
                      setUploadError(error instanceof Error ? error.message : "The context file could not be read.");
                    }
                  }}
                  onClearSelectedFile={() => setContextUpload(null)}
                  pendingFileName={contextUpload?.file_name || null}
                  pendingFileSize={contextUpload ? Math.floor((contextUpload.content_base64.length * 3) / 4) : null}
                  savedFile={profile.context_source_file ?? null}
                />
              )}
            </form.Field>

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Saving changes…" : "Save profile"}
              </Button>
              {mutation.error ? <p className="text-sm text-rose-700">{String(mutation.error.message)}</p> : null}
              {uploadError ? <p className="text-sm text-rose-700">{uploadError}</p> : null}
              {mutation.isSuccess ? <p className="text-sm text-emerald-700">Profile updated successfully.</p> : null}
            </div>
          </form>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--page-ink)]">Version trail</h2>
          <p className="text-sm leading-6 text-[var(--muted-ink)]">
            The API stores resume and context versions separately, together with any uploaded source file metadata, so scoring tasks can always point back to the exact snapshot they used.
          </p>
          <div className="grid gap-3">
            <div className="rounded-[20px] bg-stone-100 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">Resume version</p>
              <p className="mt-2 text-3xl font-semibold text-[var(--page-ink)]">{profile.resume_version_number}</p>
            </div>
            <div className="rounded-[20px] bg-stone-100 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-ink)]">Context version</p>
              <p className="mt-2 text-3xl font-semibold text-[var(--page-ink)]">{profile.context_version_number}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
