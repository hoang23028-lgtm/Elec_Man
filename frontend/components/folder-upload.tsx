"use client";

import { useRef, useState } from "react";

import { createBatch, startBatch, uploadImage } from "@/services/batches";
import type { UploadProgress } from "@/types/batch";

type Props = { csrfToken: string; onQueued?: () => void };
const allowedExtensions = new Set(["jpg", "jpeg", "png", "webp"]);

function folderName(file: File): string {
  const path = (file as File & { webkitRelativePath?: string })
    .webkitRelativePath;
  return path?.split("/")[0] || "meter-images";
}

export function FolderUpload({ csrfToken, onQueued }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [failedFiles, setFailedFiles] = useState<File[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [progress, setProgress] = useState<UploadProgress>({
    total: 0,
    uploaded: 0,
    failed: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const completed = progress.uploaded + progress.failed;
  const remaining = Math.max(progress.total - completed, 0);
  const percentage = progress.total
    ? Math.round((completed / progress.total) * 100)
    : 0;

  function selectFiles(selected: FileList | null) {
    const valid = Array.from(selected ?? []).filter((file) =>
      allowedExtensions.has(file.name.split(".").pop()?.toLowerCase() ?? ""),
    );
    setFiles(valid);
    setFailedFiles([]);
    setBatchId(null);
    setProgress({ total: valid.length, uploaded: 0, failed: 0 });
    setError(
      valid.length ? null : "Hãy chọn thư mục chứa ảnh JPEG, PNG hoặc WEBP.",
    );
    setProcessingStatus(null);
  }

  async function transfer(
    targetBatchId: string,
    targetFiles: File[],
  ): Promise<File[]> {
    const failures: File[] = [];
    let cursor = 0;
    async function worker() {
      while (cursor < targetFiles.length) {
        const file = targetFiles[cursor++];
        try {
          await uploadImage(targetBatchId, file, csrfToken);
          setProgress((current) => ({
            ...current,
            uploaded: current.uploaded + 1,
          }));
        } catch {
          failures.push(file);
          setProgress((current) => ({
            ...current,
            failed: current.failed + 1,
          }));
        }
      }
    }
    await Promise.all(
      Array.from({ length: Math.min(5, targetFiles.length) }, worker),
    );
    setFailedFiles(failures);
    return failures;
  }

  async function startUpload() {
    if (!files.length) return;
    setUploading(true);
    setError(null);
    try {
      const batch = await createBatch(folderName(files[0]), csrfToken);
      setBatchId(batch.id);
      const failures = await transfer(batch.id, files);
      if (!failures.length) {
        const queued = await startBatch(batch.id, csrfToken);
        setProcessingStatus(
          `${queued.batch_code} đã được đưa vào hàng đợi xử lý OCR bằng AI.`,
        );
        onQueued?.();
        setFiles([]);
        if (inputRef.current) inputRef.current.value = "";
      }
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể tạo lô dữ liệu.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function retryFailed() {
    if (!batchId || !failedFiles.length) return;
    const retryFiles = failedFiles;
    setProgress((current) => ({ ...current, failed: 0 }));
    setFailedFiles([]);
    setUploading(true);
    setError(null);
    try {
      const failures = await transfer(batchId, retryFiles);
      if (!failures.length) {
        const queued = await startBatch(batchId, csrfToken);
        setProcessingStatus(
          `${queued.batch_code} đã được đưa vào hàng đợi xử lý OCR bằng AI.`,
        );
        onQueued?.();
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể thử tải lại các tệp bị lỗi.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function queueForProcessing() {
    if (!batchId) return;
    setError(null);
    try {
      const batch = await startBatch(batchId, csrfToken);
      setProcessingStatus(
        `${batch.batch_code} đã được đưa vào hàng đợi xử lý OCR bằng AI.`,
      );
      onQueued?.();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể đưa lô này vào hàng đợi.",
      );
    }
  }

  return (
    <section className="panel" aria-labelledby="upload-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Bước 1</p>
          <h2 id="upload-title">Tải ảnh đồng hồ điện</h2>
        </div>
        <span className="badge active">OCR cơ sở</span>
      </div>
      <p className="muted">
        Chọn một thư mục. Các ảnh hợp lệ sẽ được tải lên qua năm luồng đồng thời
        và tự động đưa vào hàng đợi.
      </p>
      <input
        ref={(element) => {
          inputRef.current = element;
          element?.setAttribute("webkitdirectory", "");
        }}
        type="file"
        multiple
        onChange={(event) => selectFiles(event.target.files)}
        aria-label="Chọn thư mục ảnh"
      />
      <div className="progress-block" aria-live="polite">
        <div
          className="progress-track"
          role="progressbar"
          aria-label="Tiến độ tải lên"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percentage}
        >
          <span style={{ width: `${percentage}%` }} />
        </div>
        <p className="progress">
          Đã chọn {progress.total} · Đã tải {progress.uploaded} · Lỗi{" "}
          {progress.failed} · Còn lại {remaining} · {percentage}%
        </p>
      </div>
      <button
        type="button"
        onClick={startUpload}
        disabled={uploading || !files.length}
      >
        {uploading ? "Đang tải lên…" : "Tải lên và xử lý"}
      </button>
      {failedFiles.length > 0 && (
        <button
          className="secondary"
          type="button"
          onClick={retryFailed}
          disabled={uploading}
        >
          Thử tải lại {failedFiles.length} tệp bị lỗi
        </button>
      )}
      {batchId &&
        progress.uploaded === progress.total &&
        !progress.failed &&
        !processingStatus && (
          <button type="button" onClick={queueForProcessing}>
            Đưa vào hàng đợi xử lý
          </button>
        )}
      {processingStatus && (
        <p className="notice" role="status">
          {processingStatus}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
