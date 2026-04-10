import { useForm } from "@tanstack/react-form";
import { useNavigate } from "@tanstack/react-router";
import { startTransition, useState } from "react";

import { ProfileDocumentField } from "@/components/profile-document-field";
import { Card, Field, TextInput, PageHeader, Button } from "@/components/ui";
import { useCreateProfileMutation } from "@/lib/api/hooks";
import { fileToUploadPayload, type UploadedProfileDocumentPayload } from "@/lib/uploads";

export function OnboardingPage() {
  const navigate = useNavigate();
  const mutation = useCreateProfileMutation();
  const [resumeUpload, setResumeUpload] = useState<UploadedProfileDocumentPayload | null>(null);
  const [contextUpload, setContextUpload] = useState<UploadedProfileDocumentPayload | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const form = useForm({
    defaultValues: {
      display_name: "",
      location: "",
      resume_text: "",
      context_text: "",
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync({
        ...value,
        resume_upload: resumeUpload,
        context_upload: contextUpload,
      });
      setResumeUpload(null);
      setContextUpload(null);
      startTransition(() => {
        void navigate({ to: "/app/dashboard" });
      });
    },
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Onboarding"
        title="Build your first profile snapshot"
        description="This is the browser equivalent of the CLI resume and context files. Once saved, the API can attach the profile to every job you create."
      />

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
                  <TextInput
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                    placeholder="Mohammad Naderi"
                  />
                </Field>
              )}
            </form.Field>
            <form.Field name="location">
              {(field) => (
                <Field label="Location">
                  <TextInput
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                    placeholder="London, UK"
                  />
                </Field>
              )}
            </form.Field>
          </div>

          <form.Field name="resume_text">
            {(field) => (
              <ProfileDocumentField
                label="Resume text"
                hint="Paste your resume or upload the source file. If the text box is empty, the backend will extract readable text from the uploaded file."
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
                savedFile={null}
              />
            )}
          </form.Field>

          <form.Field name="context_text">
            {(field) => (
              <ProfileDocumentField
                label="Honest context"
                hint="Paste the stable context yourself, or upload a file if you keep it separately."
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
                savedFile={null}
              />
            )}
          </form.Field>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving profile…" : "Create profile"}
            </Button>
            {mutation.error ? <p className="text-sm text-rose-700">{String(mutation.error.message)}</p> : null}
            {uploadError ? <p className="text-sm text-rose-700">{uploadError}</p> : null}
          </div>
        </form>
      </Card>
    </div>
  );
}
