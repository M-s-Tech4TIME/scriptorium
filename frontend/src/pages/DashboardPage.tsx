import { IconBook2, IconPlus, IconWorld, IconLock } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, api } from "../api/client";
import type { Athenaeum } from "../api/types";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  Input,
  Modal,
  Spinner,
} from "../components/ui";
import { isSlug, slugify } from "../lib/format";

function CreateAthenaeumDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.createAthenaeum({ title: title.trim(), slug }),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["athenaeums"] });
      onOpenChange(false);
      setTitle("");
      setSlug("");
      setSlugTouched(false);
      navigate(`/a/${created.id}`);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not create library.",
      ),
  });

  const submit = () => {
    setError(null);
    if (!title.trim()) {
      setError("A title is required.");
      return;
    }
    if (!isSlug(slug)) {
      setError("Slug must use lowercase letters, numbers, and hyphens.");
      return;
    }
    mutation.mutate();
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="New library">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <ErrorBanner message={error} />
        <Field label="Title">
          <Input
            value={title}
            autoFocus
            placeholder="Product handbook"
            onChange={(event) => {
              const next = event.target.value;
              setTitle(next);
              if (!slugTouched) setSlug(slugify(next));
            }}
          />
        </Field>
        <Field
          label="Editor slug"
          hint="Lowercase letters, numbers, and hyphens. Public URLs use a separate name."
        >
          <Input
            value={slug}
            placeholder="product-handbook"
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(slugify(event.target.value));
            }}
          />
        </Field>
        <div className="dialog-actions">
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating…" : "Create library"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function AthenaeumCard({ athenaeum }: { athenaeum: Athenaeum }) {
  return (
    <Link to={`/a/${athenaeum.id}`} className="library-card">
      <div className="library-card-top">
        <span className="library-icon" aria-hidden="true">
          <IconBook2 size={22} stroke={1.7} />
        </span>
        <span
          className={`visibility-pill ${athenaeum.is_public ? "public" : ""}`}
        >
          {athenaeum.is_public ? (
            <IconWorld size={13} aria-hidden="true" />
          ) : (
            <IconLock size={13} aria-hidden="true" />
          )}
          {athenaeum.is_public ? "Public" : "Private"}
        </span>
      </div>
      <h3>{athenaeum.title}</h3>
      <p className="library-slug">/a/{athenaeum.public_slug}/</p>
    </Link>
  );
}

export function DashboardPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const athenaeums = useQuery({
    queryKey: ["athenaeums"],
    queryFn: api.listAthenaeums,
  });
  const grimoires = useQuery({
    queryKey: ["grimoires"],
    queryFn: api.listGrimoires,
  });

  const shared = (grimoires.data ?? []).filter((g) => g.role !== "owner");

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Library desk</p>
          <h1>Your Athenaeums</h1>
          <p className="muted">
            Each library is one published documentation site. Grimoires are the
            books inside it.
          </p>
        </div>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>
          <IconPlus size={17} aria-hidden="true" />
          New library
        </Button>
      </header>

      {athenaeums.isLoading ? (
        <Spinner label="Loading libraries…" />
      ) : athenaeums.isError ? (
        <ErrorBanner
          message={
            athenaeums.error instanceof ApiError
              ? athenaeums.error.message
              : "Could not load libraries."
          }
        />
      ) : athenaeums.data?.length ? (
        <div className="library-grid">
          {athenaeums.data.map((athenaeum) => (
            <AthenaeumCard key={athenaeum.id} athenaeum={athenaeum} />
          ))}
        </div>
      ) : (
        <EmptyState title="No libraries yet">
          <p>
            Create your first Athenaeum, then add a grimoire and start writing.
          </p>
          <Button variant="primary" onClick={() => setCreateOpen(true)}>
            Create a library
          </Button>
        </EmptyState>
      )}

      {shared.length ? (
        <section className="section">
          <div className="section-head">
            <h2>Shared with you</h2>
            <p className="muted">
              Grimoires where you are an editor or viewer.
            </p>
          </div>
          <div className="shared-list">
            {shared.map((grimoire) => (
              <Link
                key={grimoire.id}
                to={`/g/${grimoire.id}`}
                className="shared-row"
              >
                <span>
                  <strong>{grimoire.title}</strong>
                  <span className="muted"> · {grimoire.source_format}</span>
                </span>
                <span className="role-pill">{grimoire.role}</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <CreateAthenaeumDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
