import {
  IconChevronRight,
  IconFileText,
  IconFolder,
  IconPencil,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, api } from "../api/client";
import type { TreeNode } from "../api/types";
import {
  Button,
  ConfirmDialog,
  ErrorBanner,
  Field,
  IconButton,
  Input,
  Modal,
} from "../components/ui";
import { isSlug, slugify } from "../lib/format";

function AddNodeDialog({
  grimoireId,
  parentId,
  open,
  onOpenChange,
  onCreated,
}: {
  grimoireId: string;
  parentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (node: TreeNode) => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [kind, setKind] = useState<"chapter" | "folio">("folio");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.createNode(grimoireId, {
        parent_id: parentId,
        kind,
        title: title.trim(),
        slug,
      }),
    onSuccess: async (node) => {
      await queryClient.invalidateQueries({ queryKey: ["tree", grimoireId] });
      onOpenChange(false);
      setTitle("");
      setSlug("");
      setSlugTouched(false);
      setKind("folio");
      onCreated(node);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not create page.",
      ),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="New page">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          if (!title.trim() || !isSlug(slug)) {
            setError("A title and a valid slug are required.");
            return;
          }
          create.mutate();
        }}
      >
        <ErrorBanner message={error} />
        <Field label="Title">
          <Input
            autoFocus
            value={title}
            placeholder="Getting started"
            onChange={(event) => {
              const next = event.target.value;
              setTitle(next);
              if (!slugTouched) setSlug(slugify(next));
            }}
          />
        </Field>
        <Field label="Slug" hint="Lowercase letters, numbers, and hyphens.">
          <Input
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(slugify(event.target.value));
            }}
          />
        </Field>
        <Field
          label="Kind"
          hint="Chapters can hold child pages; folios are leaves."
        >
          <select
            className="input"
            value={kind}
            onChange={(event) =>
              setKind(event.target.value as "chapter" | "folio")
            }
          >
            <option value="folio">Folio</option>
            <option value="chapter">Chapter</option>
          </select>
        </Field>
        <div className="dialog-actions">
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create page"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RenameNodeDialog({
  grimoireId,
  node,
  open,
  onOpenChange,
  onRenamed,
}: {
  grimoireId: string;
  node: TreeNode | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRenamed: () => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(node?.title ?? "");
  const [slug, setSlug] = useState(node?.slug ?? "");
  const [error, setError] = useState<string | null>(null);

  const rename = useMutation({
    mutationFn: () =>
      api.patchNode(grimoireId, node!.id, { title: title.trim(), slug }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tree", grimoireId] });
      onOpenChange(false);
      onRenamed();
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not rename page.",
      ),
  });

  if (!node) return null;
  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Rename page">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          if (!title.trim() || !isSlug(slug)) {
            setError("A title and a valid slug are required.");
            return;
          }
          rename.mutate();
        }}
      >
        <ErrorBanner message={error} />
        <Field label="Title">
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </Field>
        <Field
          label="Slug"
          hint="Changing this changes page paths in future builds."
        >
          <Input
            value={slug}
            onChange={(event) => setSlug(slugify(event.target.value))}
          />
        </Field>
        <div className="dialog-actions">
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={rename.isPending}>
            {rename.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function NodeRow({
  node,
  depth,
  selectedId,
  canEdit,
  onSelect,
  onAddChild,
  onRename,
  onDelete,
}: {
  node: TreeNode;
  depth: number;
  selectedId: string | null;
  canEdit: boolean;
  onSelect: (node: TreeNode) => void;
  onAddChild: (node: TreeNode) => void;
  onRename: (node: TreeNode) => void;
  onDelete: (node: TreeNode) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  return (
    <li>
      <div
        className={`tree-row ${selectedId === node.id ? "selected" : ""}`.trim()}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        <button
          type="button"
          className="tree-toggle"
          aria-label={expanded ? "Collapse children" : "Expand children"}
          disabled={!hasChildren}
          onClick={() => setExpanded((value) => !value)}
        >
          <IconChevronRight
            size={14}
            className={expanded ? "chevron-open" : ""}
            aria-hidden="true"
          />
        </button>
        <button
          type="button"
          className="tree-label"
          onClick={() => onSelect(node)}
        >
          {node.kind === "chapter" ? (
            <IconFolder size={16} aria-hidden="true" />
          ) : (
            <IconFileText size={16} aria-hidden="true" />
          )}
          <span>{node.title}</span>
        </button>
        {canEdit ? (
          <span className="tree-actions">
            <IconButton
              label={`Add page inside ${node.title}`}
              onClick={() => onAddChild(node)}
            >
              <IconPlus size={14} aria-hidden="true" />
            </IconButton>
            <IconButton
              label={`Rename ${node.title}`}
              onClick={() => onRename(node)}
            >
              <IconPencil size={14} aria-hidden="true" />
            </IconButton>
            <IconButton
              label={`Delete ${node.title}`}
              onClick={() => onDelete(node)}
            >
              <IconTrash size={14} aria-hidden="true" />
            </IconButton>
          </span>
        ) : null}
      </div>
      {hasChildren && expanded ? (
        <ul className="tree-list">
          {node.children.map((child) => (
            <NodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              canEdit={canEdit}
              onSelect={onSelect}
              onAddChild={onAddChild}
              onRename={onRename}
              onDelete={onDelete}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function TreePanel({
  grimoireId,
  nodes,
  selectedId,
  canEdit,
  onSelect,
  onChanged,
}: {
  grimoireId: string;
  nodes: TreeNode[];
  selectedId: string | null;
  canEdit: boolean;
  onSelect: (node: TreeNode) => void;
  onChanged: () => void;
}) {
  const queryClient = useQueryClient();
  const [addParent, setAddParent] = useState<string | null | undefined>(
    undefined,
  );
  const [renameNode, setRenameNode] = useState<TreeNode | null>(null);
  const [deleteNode, setDeleteNode] = useState<TreeNode | null>(null);
  const [error, setError] = useState<string | null>(null);

  const remove = useMutation({
    mutationFn: () => api.deleteNode(grimoireId, deleteNode!.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tree", grimoireId] });
      setDeleteNode(null);
      onChanged();
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not delete page.",
      ),
  });

  return (
    <aside className="tree-panel">
      <div className="tree-head">
        <h2>Pages</h2>
        {canEdit ? (
          <IconButton
            label="Add top-level page"
            onClick={() => setAddParent(null)}
          >
            <IconPlus size={17} aria-hidden="true" />
          </IconButton>
        ) : null}
      </div>
      <ErrorBanner message={error} />
      {nodes.length ? (
        <ul className="tree-list">
          {nodes.map((node) => (
            <NodeRow
              key={node.id}
              node={node}
              depth={0}
              selectedId={selectedId}
              canEdit={canEdit}
              onSelect={onSelect}
              onAddChild={(parent) => setAddParent(parent.id)}
              onRename={(target) => setRenameNode(target)}
              onDelete={(target) => setDeleteNode(target)}
            />
          ))}
        </ul>
      ) : (
        <p className="muted small tree-empty">
          No pages yet. Add a folio to start writing.
        </p>
      )}

      <AddNodeDialog
        key={addParent ?? "root"}
        grimoireId={grimoireId}
        parentId={addParent ?? null}
        open={addParent !== undefined}
        onOpenChange={(open) => {
          if (!open) setAddParent(undefined);
        }}
        onCreated={(node) => {
          onChanged();
          onSelect(node);
        }}
      />
      <RenameNodeDialog
        key={renameNode?.id ?? "none"}
        grimoireId={grimoireId}
        node={renameNode}
        open={Boolean(renameNode)}
        onOpenChange={(open) => {
          if (!open) setRenameNode(null);
        }}
        onRenamed={onChanged}
      />
      <ConfirmDialog
        open={Boolean(deleteNode)}
        onOpenChange={(open) => {
          if (!open) setDeleteNode(null);
        }}
        title="Delete page"
        message={
          deleteNode
            ? `Delete “${deleteNode.title}”? Pages with children or saved content are refused by the server.`
            : ""
        }
        confirmLabel="Delete"
        destructive
        busy={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </aside>
  );
}
