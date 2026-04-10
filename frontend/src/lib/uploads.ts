export type UploadedProfileDocumentPayload = {
  file_name: string;
  content_type: string | null;
  content_base64: string;
};

export async function fileToUploadPayload(file: File): Promise<UploadedProfileDocumentPayload> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  return {
    file_name: file.name,
    content_type: file.type || null,
    content_base64: bytesToBase64(bytes),
  };
}

export function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}
