import type { JSONContent } from "@tiptap/core";
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCode,
  IconDeviceFloppy,
  IconHistory,
  IconUpload,
} from "@tabler/icons-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useBlocker, useNavigate, useParams } from "react-router";

import { ApiError, api } from "../api/client";
import type { DocumentBody, Grimoire, TreeNode } from "../api/types";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorBanner,
  Modal,
  Spinner,
} from "../components/ui";
import { EditorSurface } from "../editor/EditorSurface";
import { HistoryPanel } from "../editor/HistoryPanel";
import { TreePanel } from "../editor/TreePanel";
import {
  canonicalizeMedia,
  newMediaMaps,
  resolveMedia,
  revokeMedia,
} from "../editor/media";

const EMPTY_DOC: JSONContent = {
  type: "doc",
  content: [{ type: "paragraph" }],
};

function findNode(nodes: TreeNode[], id: string): TreeNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findNode(node.children, id);
    if (child) return child;
  }
  return null;
}

function firstNode(nodes: TreeNode[]): TreeNode | null {
  return nodes[0] ?? null;
}

export function GrimoirePage() {
  const { grimoireId = "", nodeId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const maps = useRef(newMediaMaps());
  const latestJson = useRef<JSONContent | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [document, setDocument] = useState<DocumentBody | null>(null);
  const [editorContent, setEditorContent] = useState<JSONContent | null>(null);
  const [editorKey, setEditorKey] = useState(0);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [pendingImport, setPendingImport] = useState<{
    name: string;
    text: string;
  } | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const grimoire = useQuery({
    queryKey: ["grimoire", grimoireId],
    queryFn: () => api.getGrimoire(grimoireId),
    enabled: Boolean(grimoireId),
  });
  const tree = useQuery({
    queryKey: ["tree", grimoireId],
    queryFn: () => api.getTree(grimoireId),
    enabled: Boolean(grimoireId),
  });

  const selectedNode =
    tree.data && nodeId ? findNode(tree.data.nodes, nodeId) : null;
  const canEdit =
    grimoire.data?.role === "owner" || grimoire.data?.role === "editor";
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty && currentLocation.pathname !== nextLocation.pathname,
  );

  useEffect(() => {
    if (!tree.data || nodeId) return;
    const first = firstNode(tree.data.nodes);
    if (first) {
      navigate(`/g/${grimoireId}/n/${first.id}`, { replace: true });
    }
  }, [tree.data, nodeId, grimoireId, navigate]);

  useEffect(() => {
    if (!nodeId) return;
    let cancelled = false;
    setDocumentLoading(true);
    setDocumentError(null);
    setSaveError(null);
    setConflict(null);
    setDirty(false);
    setDocument(null);
    setEditorContent(null);
    revokeMedia(maps.current);
    latestJson.current = null;

    (async () => {
      try {
        const loaded = await api.getDocument(grimoireId, nodeId);
        const content = await resolveMedia(loaded.tiptap_json, maps.current);
        if (cancelled) return;
        setDocument(loaded);
        setEditorContent(content);
        setEditorKey((key) => key + 1);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setDocument(null);
          setEditorContent(EMPTY_DOC);
          setEditorKey((key) => key + 1);
        } else {
          setDocumentError(
            err instanceof ApiError ? err.message : "Could not load this page.",
          );
        }
      } finally {
        if (!cancelled) setDocumentLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [grimoireId, nodeId]);

  useEffect(() => {
    return () => revokeMedia(maps.current);
  }, []);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const applyDocument = async (next: DocumentBody) => {
    const content = await resolveMedia(next.tiptap_json, maps.current);
    setDocument(next);
    setEditorContent(content);
    setEditorKey((key) => key + 1);
    setDirty(false);
    setConflict(null);
    latestJson.current = content;
  };

  const save = async (json: unknown) => {
    if (!nodeId || !canEdit) return;
    setSaving(true);
    setSaveError(null);
    try {
      const canonical = canonicalizeMedia(json as JSONContent, maps.current);
      const saved = await api.putDocument(grimoireId, nodeId, {
        tiptap_json: canonical,
        expected_version: document?.version ?? 0,
      });
      setDocument(saved);
      setDirty(false);
      setConflict(null);
      await queryClient.invalidateQueries({
        queryKey: ["history", grimoireId, nodeId],
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict(err.message);
      } else {
        setSaveError(err instanceof ApiError ? err.message : "Could not save.");
      }
    } finally {
      setSaving(false);
    }
  };

  const reloadLatest = async () => {
    if (!nodeId) return;
    setDocumentLoading(true);
    setSaveError(null);
    try {
      const loaded = await api.getDocument(grimoireId, nodeId);
      await applyDocument(loaded);
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : "Could not reload the document.",
      );
    } finally {
      setDocumentLoading(false);
    }
  };

  const overwrite = async () => {
    if (!nodeId || !canEdit) return;
    setSaving(true);
    setSaveError(null);
    try {
      let current: DocumentBody | null = null;
      try {
        current = await api.getDocument(grimoireId, nodeId);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) throw err;
      }
      const canonical = canonicalizeMedia(
        (latestJson.current ?? editorContent ?? EMPTY_DOC) as JSONContent,
        maps.current,
      );
      const saved = await api.putDocument(grimoireId, nodeId, {
        tiptap_json: canonical,
        expected_version: current?.version ?? 0,
      });
      setDocument(saved);
      setDirty(false);
      setConflict(null);
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : "Could not overwrite the document.",
      );
    } finally {
      setSaving(false);
    }
  };

  const importSource = async (text: string) => {
    if (!nodeId || !canEdit) return;
    setSaving(true);
    setImportError(null);
    try {
      const saved = await api.putDocument(grimoireId, nodeId, {
        source_text: text,
        expected_version: document?.version ?? 0,
      });
      await applyDocument(saved);
      await queryClient.invalidateQueries({
        queryKey: ["history", grimoireId, nodeId],
      });
    } catch (err) {
      setImportError(
        err instanceof ApiError ? err.message : "Could not import that file.",
      );
    } finally {
      setSaving(false);
    }
  };

  const uploadImage = async (file: File): Promise<string | null> => {
    setSaveError(null);
    try {
      const asset = await api.uploadMedia(grimoireId, file);
      const blobUrl = URL.createObjectURL(file);
      maps.current.canonicalToBlob.set(asset.url, blobUrl);
      maps.current.blobToCanonical.set(blobUrl, asset.url);
      return blobUrl;
    } catch (err) {
      setSaveError(
        err instanceof ApiError ? err.message : "Could not upload the image.",
      );
      return null;
    }
  };

  if (grimoire.isLoading) {
    return (
      <div className="page">
        <Spinner label="Opening grimoire…" />
      </div>
    );
  }
  if (grimoire.isError || !grimoire.data) {
    return (
      <div className="page">
        <ErrorBanner
          message={
            grimoire.error instanceof ApiError
              ? grimoire.error.message
              : "Grimoire not found."
          }
        />
        <Link to="/" className="text-link">
          Back to libraries
        </Link>
      </div>
    );
  }

  const book: Grimoire = grimoire.data;

  return (
    <div className="editor-shell-page">
      <header className="editor-head">
        <div className="editor-head-left">
          <Link to={`/a/${book.athenaeum_id}`} className="back-link">
            <IconArrowLeft size={16} aria-hidden="true" />
            Library
          </Link>
          <div>
            <div className="title-with-pill">
              <h1>{book.title}</h1>
              <span className="role-pill">{book.role}</span>
              <span className="format-pill">
                {book.source_format === "myst" ? "MyST" : "RST"}
              </span>
            </div>
            <p className="muted small">
              {selectedNode ? selectedNode.title : "Select a page"}
              {dirty
                ? " · Unsaved changes"
                : document
                  ? ` · v${document.version}`
                  : ""}
            </p>
          </div>
        </div>
        <div className="head-actions">
          <input
            ref={fileRef}
            type="file"
            hidden
            accept={
              book.source_format === "rst" ? ".rst" : ".md,.myst,.markdown"
            }
            onChange={async (event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (!file) return;
              setImportError(null);
              const text = await file.text();
              setPendingImport({ name: file.name, text });
            }}
          />
          <Button
            onClick={() => fileRef.current?.click()}
            disabled={!canEdit || !nodeId}
          >
            <IconUpload size={16} aria-hidden="true" />
            Import
          </Button>
          <Button onClick={() => setSourceOpen(true)} disabled={!document}>
            <IconCode size={16} aria-hidden="true" />
            Source
          </Button>
          <Button
            onClick={() => setHistoryOpen((open) => !open)}
            disabled={!nodeId}
          >
            <IconHistory size={16} aria-hidden="true" />
            History
          </Button>
          <Button
            variant="primary"
            onClick={() =>
              save(latestJson.current ?? editorContent ?? EMPTY_DOC)
            }
            disabled={!canEdit || !dirty || saving || !nodeId}
          >
            <IconDeviceFloppy size={16} aria-hidden="true" />
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </header>

      <ErrorBanner message={saveError} />
      {conflict ? (
        <div className="conflict-banner" role="alert">
          <IconAlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>Someone saved a newer version.</strong>
            <p>{conflict}</p>
          </div>
          <div className="conflict-actions">
            <Button onClick={() => void reloadLatest()}>Reload latest</Button>
            <Button variant="danger" onClick={() => void overwrite()}>
              Overwrite with mine
            </Button>
          </div>
        </div>
      ) : null}

      <div
        className={`editor-layout ${historyOpen ? "with-history" : ""}`.trim()}
      >
        <TreePanel
          grimoireId={grimoireId}
          nodes={tree.data?.nodes ?? []}
          selectedId={nodeId ?? null}
          canEdit={canEdit}
          onSelect={(node) => navigate(`/g/${grimoireId}/n/${node.id}`)}
          onChanged={() => {
            void queryClient.invalidateQueries({
              queryKey: ["tree", grimoireId],
            });
          }}
        />

        <section className="editor-main">
          {!nodeId ? (
            <EmptyState title="Choose a page">
              <p>Select a folio in the tree, or add a new one.</p>
            </EmptyState>
          ) : documentLoading || !editorContent ? (
            <Spinner label="Loading page…" />
          ) : documentError ? (
            <ErrorBanner message={documentError} />
          ) : (
            <EditorSurface
              key={`${nodeId}:${editorKey}`}
              initialContent={editorContent}
              canEdit={canEdit}
              saving={saving}
              onSave={(json) => void save(json)}
              onChange={(json) => {
                latestJson.current = json as JSONContent;
              }}
              onDirtyChange={setDirty}
              onUploadImage={uploadImage}
            />
          )}
        </section>

        {historyOpen && nodeId ? (
          <aside className="history-drawer">
            <div className="tree-head">
              <h2>History</h2>
              <Button variant="ghost" onClick={() => setHistoryOpen(false)}>
                Close
              </Button>
            </div>
            <HistoryPanel
              grimoireId={grimoireId}
              nodeId={nodeId}
              currentVersion={document?.version ?? 0}
              canEdit={canEdit}
              onRestored={(restored) => void applyDocument(restored)}
            />
          </aside>
        ) : null}
      </div>

      <Modal
        open={sourceOpen}
        onOpenChange={setSourceOpen}
        title="Generated source"
        wide
      >
        <p className="muted small">
          Server-derived from the last saved canonical document.
        </p>
        <pre className="source-preview">{document?.source_text ?? ""}</pre>
        <div className="dialog-actions">
          <Button onClick={() => setSourceOpen(false)}>Close</Button>
        </div>
      </Modal>

      <ConfirmDialog
        open={blocker.state === "blocked"}
        onOpenChange={(open) => {
          if (!open && blocker.state === "blocked") blocker.reset();
        }}
        title="Discard unsaved changes?"
        message="This page has changes that have not been saved. Leaving now discards them."
        confirmLabel="Discard and leave"
        destructive
        onConfirm={() => {
          if (blocker.state === "blocked") blocker.proceed();
        }}
      />
      <ConfirmDialog
        open={Boolean(pendingImport)}
        onOpenChange={(open) => {
          if (!open) setPendingImport(null);
        }}
        title="Import source file"
        message={
          pendingImport
            ? `Replace the editor content with “${pendingImport.name}”? The current version stays in history.`
            : ""
        }
        confirmLabel="Import and save"
        busy={saving}
        onConfirm={() => {
          if (!pendingImport) return;
          const text = pendingImport.text;
          setPendingImport(null);
          void importSource(text);
        }}
      />
      <Modal
        open={Boolean(importError)}
        onOpenChange={() => setImportError(null)}
        title="Import failed"
      >
        <ErrorBanner message={importError} />
        <div className="dialog-actions">
          <Button onClick={() => setImportError(null)}>Close</Button>
        </div>
      </Modal>
    </div>
  );
}
