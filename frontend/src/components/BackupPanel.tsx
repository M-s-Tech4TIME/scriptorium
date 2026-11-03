import { IconDownload, IconUpload } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { ApiError, api } from "../api/client";
import type {
  BackupExport,
  BackupFormat,
  BackupJob,
  BackupMode,
  BackupRestoreResult,
} from "../api/types";
import { saveBlob } from "../lib/download";
import { formatDate } from "../lib/format";
import { Button, ErrorBanner, Field, Spinner } from "./ui";

function formatBytes(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  if (value < 1024) return `${value} B`;
  const units = ["KiB", "MiB", "GiB", "TiB"] as const;
  let size = value / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unit] ?? "KiB"}`;
}

function jobFailure(job: BackupJob | undefined): string | null {
  if (!job || job.status !== "failed") return null;
  return job.error ?? "The backup worker reported a failure.";
}

function JobProgress({ job }: { job: BackupJob }) {
  if (job.status === "queued" || job.status === "running") {
    return (
      <p className="muted small" role="status">
        {job.status === "queued"
          ? "Queued for the backup worker…"
          : "Working on the archive…"}
      </p>
    );
  }
  return null;
}

export function BackupPanel({ athenaeumId }: { athenaeumId: string }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<BackupMode>("editorial");
  const [format, setFormat] = useState<BackupFormat>("zip");
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exported, setExported] = useState<BackupExport | null>(null);
  const [downloaded, setDownloaded] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoreJobId, setRestoreJobId] = useState<string | null>(null);
  const [restored, setRestored] = useState<BackupRestoreResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportJob = useQuery({
    queryKey: ["backup-job", exportJobId],
    queryFn: () => api.getBackupJob(exportJobId ?? ""),
    enabled: Boolean(exportJobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      return job && (job.status === "queued" || job.status === "running")
        ? 1500
        : false;
    },
  });

  const restoreJob = useQuery({
    queryKey: ["backup-job", restoreJobId],
    queryFn: () => api.getBackupJob(restoreJobId ?? ""),
    enabled: Boolean(restoreJobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      return job && (job.status === "queued" || job.status === "running")
        ? 1500
        : false;
    },
  });

  const restoreJobStatus = restoreJob.data?.status;
  useEffect(() => {
    if (restoreJobStatus !== "ok") return;
    void queryClient.invalidateQueries({ queryKey: ["athenaeums"] });
    void queryClient.invalidateQueries({ queryKey: ["grimoires"] });
  }, [restoreJobStatus, queryClient]);

  const restoredSiteId =
    restoreJob.data?.status === "ok"
      ? restoreJob.data.result_athenaeum_id
      : null;
  const restoredSite = useQuery({
    queryKey: ["athenaeum", restoredSiteId],
    queryFn: () => api.getAthenaeum(restoredSiteId ?? ""),
    enabled: Boolean(restoredSiteId),
  });

  const exportMutation = useMutation({
    mutationFn: () => api.exportBackup(athenaeumId, mode, format),
    onMutate: () => {
      setError(null);
      setExported(null);
      setExportJobId(null);
      setDownloaded(false);
    },
    onSuccess: (result) => {
      if ("blob" in result) {
        saveBlob(result.blob, result.filename);
        setExported(result);
      } else {
        setExportJobId(result.id);
      }
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not export the library.",
      ),
  });

  const restoreMutation = useMutation({
    mutationFn: (file: File) => api.restoreBackup(file),
    onMutate: () => {
      setError(null);
      setRestored(null);
      setRestoreJobId(null);
    },
    onSuccess: (result) => {
      if ("public_slug" in result) {
        setRestored(result);
        void queryClient.invalidateQueries({ queryKey: ["athenaeums"] });
        void queryClient.invalidateQueries({ queryKey: ["grimoires"] });
      } else {
        setRestoreJobId(result.id);
      }
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not restore the backup.",
      ),
  });

  const fullJob = exportJob.data;
  const fullJobError = jobFailure(fullJob);

  return (
    <section className="section backup-section" aria-labelledby="backup-title">
      <div className="section-head">
        <h2 id="backup-title">Backup &amp; restore</h2>
        <p className="muted">
          Take this library out of Scriptorium, or restore an archive as a new
          library. Restoring never merges into an existing site.
        </p>
      </div>

      <ErrorBanner message={error} />

      <div className="backup-grid">
        <div className="backup-card">
          <div className="section-head">
            <h3>Export</h3>
            <p className="muted small">
              {mode === "editorial"
                ? "Content, media, names, and every published successful build with its served artifacts."
                : "Everything in Editorial plus failed builds, build logs, and artifacts for every successful build."}
            </p>
          </div>
          <Field label="Contents">
            <select
              className="input"
              value={mode}
              onChange={(event) => setMode(event.target.value as BackupMode)}
            >
              <option value="editorial">Editorial — portable content</option>
              <option value="full">Full — server-move fidelity</option>
            </select>
          </Field>
          <Field label="Container">
            <select
              className="input"
              value={format}
              onChange={(event) =>
                setFormat(event.target.value as BackupFormat)
              }
            >
              <option value="zip">ZIP (.zip)</option>
              <option value="tar.gz">gzip tarball (.tar.gz)</option>
            </select>
          </Field>
          <Button
            variant="primary"
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
          >
            <IconDownload size={16} aria-hidden="true" />
            {exportMutation.isPending ? "Preparing…" : "Export backup"}
          </Button>

          {exported ? (
            <div className="backup-result" role="status">
              <p className="small">
                <strong>Downloaded</strong> {exported.filename} ·{" "}
                {formatBytes(exported.size_bytes)}
              </p>
              {exported.sha256 ? (
                <p className="muted small backup-hash">
                  SHA-256 <code>{exported.sha256}</code>
                </p>
              ) : null}
            </div>
          ) : null}

          {exportJobId && !fullJob ? (
            <Spinner label="Preparing archive…" />
          ) : null}
          {fullJob ? <JobProgress job={fullJob} /> : null}
          <ErrorBanner message={fullJobError} />
          {fullJob?.status === "ok" ? (
            <div className="backup-result" role="status">
              <p className="small">
                <strong>Full backup ready</strong> ·{" "}
                {formatBytes(fullJob.size_bytes)} · {fullJob.format}
              </p>
              {fullJob.download_url && !downloaded ? (
                <a
                  className="button button-primary"
                  href={fullJob.download_url}
                  onClick={() => setDownloaded(true)}
                >
                  <IconDownload size={16} aria-hidden="true" />
                  Download archive
                </a>
              ) : (
                <p className="muted small">
                  The single-use download link was used or expired. Export again
                  to create a new archive.
                </p>
              )}
              {fullJob.expires_at ? (
                <p className="muted small">
                  Link expires {formatDate(fullJob.expires_at)}. The archive is
                  deleted after download or expiry.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="backup-card">
          <div className="section-head">
            <h3>Restore</h3>
            <p className="muted small">
              The archive is verified before anything is written. A successful
              restore creates a new library owned by you and keeps its build
              numbers and public names when they are available.
            </p>
          </div>
          <Field
            label="Backup archive"
            hint="ZIP or .tar.gz; the container is detected from the file, not its name."
          >
            <input
              className="input"
              type="file"
              accept=".zip,.tar.gz,.tgz,application/zip,application/gzip"
              onChange={(event) => {
                setRestoreFile(event.target.files?.[0] ?? null);
                setError(null);
                setRestored(null);
                setRestoreJobId(null);
              }}
            />
          </Field>
          <Button
            variant="primary"
            onClick={() => {
              if (restoreFile) restoreMutation.mutate(restoreFile);
            }}
            disabled={!restoreFile || restoreMutation.isPending}
          >
            <IconUpload size={16} aria-hidden="true" />
            {restoreMutation.isPending ? "Restoring…" : "Restore backup"}
          </Button>

          {restoreJobId && !restoreJob.data ? (
            <Spinner label="Uploading and checking the archive…" />
          ) : null}
          {restoreJob.data ? <JobProgress job={restoreJob.data} /> : null}
          <ErrorBanner message={jobFailure(restoreJob.data)} />

          {restored ? (
            <div className="backup-result" role="status">
              <p className="small">
                <strong>Restored</strong> {restored.title} as{" "}
                <code>/a/{restored.public_slug}/</code>
              </p>
              <Link className="text-link" to={`/a/${restored.athenaeum_id}`}>
                Open the restored library
              </Link>
              {restored.warnings.length ? (
                <ul className="backup-warnings">
                  {restored.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {restoreJob.data?.status === "ok" ? (
            <div className="backup-result" role="status">
              <p className="small">
                <strong>Restored</strong>{" "}
                {restoredSite.data ? (
                  <>
                    {restoredSite.data.title} as{" "}
                    <code>/a/{restoredSite.data.public_slug}/</code>
                  </>
                ) : (
                  "as a new library."
                )}
              </p>
              {restoredSiteId ? (
                <Link className="text-link" to={`/a/${restoredSiteId}`}>
                  Open the restored library
                </Link>
              ) : null}
              <p className="muted small">
                Alias conflicts, if any, are recorded in the restore audit
                entry.
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
