import { IconHistory, IconRestore } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, api } from "../api/client";
import type { DocumentBody, HistoryVersion } from "../api/types";
import { Button, ErrorBanner, Modal, Spinner } from "../components/ui";
import { formatDate } from "../lib/format";

export function HistoryPanel({
  grimoireId,
  nodeId,
  currentVersion,
  canEdit,
  onRestored,
}: {
  grimoireId: string;
  nodeId: string;
  currentVersion: number;
  canEdit: boolean;
  onRestored: (document: DocumentBody) => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<HistoryVersion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const history = useQuery({
    queryKey: ["history", grimoireId, nodeId],
    queryFn: () => api.getHistory(grimoireId, nodeId),
    retry: false,
  });

  const restore = useMutation({
    mutationFn: (version: number) =>
      api.restoreHistory(grimoireId, nodeId, version, currentVersion),
    onSuccess: async (document) => {
      await queryClient.invalidateQueries({
        queryKey: ["history", grimoireId, nodeId],
      });
      setSelected(null);
      onRestored(document);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not restore this version.",
      ),
  });

  if (history.isLoading) return <Spinner label="Loading history…" />;
  if (history.isError) {
    return <p className="muted small">No saved versions yet.</p>;
  }

  const versions = history.data?.versions ?? [];
  return (
    <div className="history-panel">
      <ErrorBanner message={error} />
      {versions.length ? (
        <ol className="history-list">
          {[...versions].reverse().map((entry) => (
            <li key={entry.version}>
              <button
                type="button"
                className="history-row"
                onClick={async () => {
                  setError(null);
                  try {
                    const detail = await api.getHistoryVersion(
                      grimoireId,
                      nodeId,
                      entry.version,
                    );
                    setSelected(detail);
                  } catch (err) {
                    setError(
                      err instanceof ApiError
                        ? err.message
                        : "Could not load that version.",
                    );
                  }
                }}
              >
                <span>
                  <strong>Version {entry.version}</strong>
                  <span className="muted small"> · {formatDate(entry.at)}</span>
                </span>
                <IconHistory size={15} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted small">No saved versions yet.</p>
      )}

      <Modal
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
        title={selected ? `Version ${selected.version}` : "Version"}
        wide
      >
        {selected ? (
          <>
            <p className="muted small">Saved {formatDate(selected.at)}</p>
            <pre className="source-preview">{selected.source_text}</pre>
            <div className="dialog-actions">
              <Button onClick={() => setSelected(null)}>Close</Button>
              {canEdit ? (
                <Button
                  variant="primary"
                  disabled={restore.isPending}
                  onClick={() => restore.mutate(selected.version)}
                >
                  <IconRestore size={16} aria-hidden="true" />
                  {restore.isPending ? "Restoring…" : "Restore this version"}
                </Button>
              ) : null}
            </div>
          </>
        ) : null}
      </Modal>
    </div>
  );
}
