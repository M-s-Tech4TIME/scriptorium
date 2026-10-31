import {
  IconBook2,
  IconExternalLink,
  IconPlus,
  IconRocket,
  IconSettings,
  IconWorld,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError, api } from "../api/client";
import type { Athenaeum, Build, Grimoire } from "../api/types";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorBanner,
  Field,
  Input,
  Modal,
  Spinner,
} from "../components/ui";
import { formatDate, isSlug, slugify } from "../lib/format";

function CreateGrimoireDialog({
  athenaeumId,
  open,
  onOpenChange,
}: {
  athenaeumId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [sourceFormat, setSourceFormat] = useState<"rst" | "myst">("rst");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.createGrimoire({
        athenaeum_id: athenaeumId,
        title: title.trim(),
        slug,
        source_format: sourceFormat,
      }),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["grimoires"] });
      onOpenChange(false);
      navigate(`/g/${created.id}`);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not create grimoire.",
      ),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="New grimoire">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          if (!title.trim() || !isSlug(slug)) {
            setError("A title and a valid slug are required.");
            return;
          }
          mutation.mutate();
        }}
      >
        <ErrorBanner message={error} />
        <Field label="Title">
          <Input
            autoFocus
            value={title}
            placeholder="Administrator guide"
            onChange={(event) => {
              const next = event.target.value;
              setTitle(next);
              if (!slugTouched) setSlug(slugify(next));
            }}
          />
        </Field>
        <Field
          label="Slug"
          hint="Used in page paths inside the published site."
        >
          <Input
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(slugify(event.target.value));
            }}
          />
        </Field>
        <Field label="Source format" hint="Immutable after creation.">
          <select
            className="input"
            value={sourceFormat}
            onChange={(event) =>
              setSourceFormat(event.target.value as "rst" | "myst")
            }
          >
            <option value="rst">reStructuredText (RST)</option>
            <option value="myst">MyST Markdown</option>
          </select>
        </Field>
        <div className="dialog-actions">
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating…" : "Create grimoire"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SettingsDialog({
  athenaeum,
  open,
  onOpenChange,
}: {
  athenaeum: Athenaeum;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(athenaeum.title);
  const [slug, setSlug] = useState(athenaeum.slug);
  const [publicSlug, setPublicSlug] = useState(athenaeum.public_slug);
  const [isPublic, setIsPublic] = useState(athenaeum.is_public);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTitle(athenaeum.title);
    setSlug(athenaeum.slug);
    setPublicSlug(athenaeum.public_slug);
    setIsPublic(athenaeum.is_public);
    setError(null);
  }, [open, athenaeum]);

  const save = useMutation({
    mutationFn: async () => {
      await api.patchAthenaeum(athenaeum.id, {
        title: title.trim(),
        slug,
        is_public: isPublic,
      });
      if (publicSlug !== athenaeum.public_slug) {
        await api.renamePublicSlug(athenaeum.id, publicSlug);
      }
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["athenaeums"] }),
        queryClient.invalidateQueries({
          queryKey: ["athenaeum", athenaeum.id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["publication", athenaeum.id],
        }),
      ]);
      onOpenChange(false);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not save settings.",
      ),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Library settings">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          if (!title.trim() || !isSlug(slug) || !isSlug(publicSlug)) {
            setError("Title and both slugs must be valid.");
            return;
          }
          save.mutate();
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
          label="Editor slug"
          hint="Internal only; never changes the public URL."
        >
          <Input
            value={slug}
            onChange={(event) => setSlug(slugify(event.target.value))}
          />
        </Field>
        <Field
          label="Public URL name"
          hint="Changing this leaves the old name as a permanent redirect."
        >
          <Input
            value={publicSlug}
            onChange={(event) => setPublicSlug(slugify(event.target.value))}
          />
        </Field>
        <label className="check-row">
          <input
            type="checkbox"
            checked={isPublic}
            onChange={(event) => setIsPublic(event.target.checked)}
          />
          <span>
            <strong>Public library</strong>
            <span className="muted">
              {" "}
              — visitors can read published channels without signing in.
            </span>
          </span>
        </label>
        <div className="dialog-actions">
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save settings"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function BuildRow({
  build,
  athenaeum,
  onPublish,
}: {
  build: Build;
  athenaeum: Athenaeum;
  onPublish: (buildId: string, channel: "latest" | "stable" | "both") => void;
}) {
  return (
    <div className="build-row">
      <div>
        <strong>Build #{build.build_number}</strong>
        <span className={`status-pill status-${build.status}`}>
          {build.status}
        </span>
        <p className="muted small">
          {build.status === "queued" || build.status === "running"
            ? "Building…"
            : `Finished ${formatDate(build.finished)}`}
        </p>
      </div>
      <div className="build-actions">
        {build.status === "ok" ? (
          <>
            <a
              className="text-link"
              href={`/a/${athenaeum.public_slug}/b/${build.build_number}/`}
              target="_blank"
              rel="noreferrer"
            >
              <IconExternalLink size={15} aria-hidden="true" />
              Open
            </a>
            <Button
              variant="ghost"
              onClick={() => onPublish(build.id, "latest")}
            >
              Latest
            </Button>
            <Button
              variant="ghost"
              onClick={() => onPublish(build.id, "stable")}
            >
              Stable
            </Button>
            <Button onClick={() => onPublish(build.id, "both")}>Publish</Button>
          </>
        ) : null}
      </div>
    </div>
  );
}

function GrimoireCard({
  grimoire,
  publicSlug,
}: {
  grimoire: Grimoire;
  publicSlug: string;
}) {
  return (
    <Link to={`/g/${grimoire.id}`} className="grimoire-card">
      <span className="grimoire-icon" aria-hidden="true">
        <IconBook2 size={20} stroke={1.7} />
      </span>
      <div>
        <h3>{grimoire.title}</h3>
        <p className="muted small">
          {grimoire.source_format === "myst" ? "MyST" : "RST"} · {grimoire.role}
        </p>
      </div>
      <span className="grimoire-path">/a/{publicSlug}/</span>
    </Link>
  );
}

export function AthenaeumPage() {
  const { athenaeumId = "" } = useParams();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmPublish, setConfirmPublish] = useState<{
    buildId: string;
    channel: "latest" | "stable" | "both";
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const athenaeum = useQuery({
    queryKey: ["athenaeum", athenaeumId],
    queryFn: () => api.getAthenaeum(athenaeumId),
    enabled: Boolean(athenaeumId),
  });
  const grimoires = useQuery({
    queryKey: ["grimoires"],
    queryFn: api.listGrimoires,
  });
  const builds = useQuery({
    queryKey: ["builds", athenaeumId],
    queryFn: () => api.listBuilds(athenaeumId),
    enabled: Boolean(athenaeumId),
    refetchInterval: (query) => {
      const rows = query.state.data;
      return rows?.some(
        (build) => build.status === "queued" || build.status === "running",
      )
        ? 2000
        : false;
    },
  });
  const publication = useQuery({
    queryKey: ["publication", athenaeumId],
    queryFn: () => api.getPublication(athenaeumId),
    enabled: Boolean(athenaeumId),
  });

  const build = useMutation({
    mutationFn: () => api.triggerBuild(athenaeumId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["builds", athenaeumId],
      });
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not start build.",
      ),
  });

  const publish = useMutation({
    mutationFn: (input: {
      buildId: string;
      channel: "latest" | "stable" | "both";
    }) => api.publish(athenaeumId, input.buildId, input.channel),
    onSuccess: async () => {
      setConfirmPublish(null);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["publication", athenaeumId],
        }),
        queryClient.invalidateQueries({ queryKey: ["athenaeum", athenaeumId] }),
        queryClient.invalidateQueries({ queryKey: ["builds", athenaeumId] }),
      ]);
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.message : "Could not publish build.",
      ),
  });

  if (athenaeum.isLoading) {
    return (
      <div className="page">
        <Spinner label="Loading library…" />
      </div>
    );
  }
  if (athenaeum.isError || !athenaeum.data) {
    return (
      <div className="page">
        <ErrorBanner
          message={
            athenaeum.error instanceof ApiError
              ? athenaeum.error.message
              : "Library not found."
          }
        />
        <Link to="/" className="text-link">
          Back to libraries
        </Link>
      </div>
    );
  }

  const lib = athenaeum.data;
  const books = (grimoires.data ?? []).filter(
    (grimoire) => grimoire.athenaeum_id === lib.id,
  );
  const building = builds.data?.some(
    (row) => row.status === "queued" || row.status === "running",
  );

  return (
    <div className="page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">Libraries</Link>
        <span aria-hidden="true">/</span>
        <span>{lib.title}</span>
      </nav>

      <header className="page-head">
        <div>
          <div className="title-with-pill">
            <h1>{lib.title}</h1>
            <span
              className={`visibility-pill ${lib.is_public ? "public" : ""}`}
            >
              <IconWorld size={13} aria-hidden="true" />
              {lib.is_public ? "Public" : "Private"}
            </span>
          </div>
          <p className="muted">
            Published at <code>/a/{lib.public_slug}/</code>
            {publication.data?.latest
              ? ` · latest build #${publication.data.latest.build_number}`
              : " · not published yet"}
          </p>
        </div>
        <div className="head-actions">
          <Button onClick={() => setSettingsOpen(true)}>
            <IconSettings size={16} aria-hidden="true" />
            Settings
          </Button>
          <Button variant="primary" onClick={() => setCreateOpen(true)}>
            <IconPlus size={17} aria-hidden="true" />
            New grimoire
          </Button>
        </div>
      </header>

      <ErrorBanner message={error} />

      <div className="library-layout">
        <section>
          <div className="section-head">
            <h2>Grimoires</h2>
            <p className="muted">The books that make up this site.</p>
          </div>
          {grimoires.isLoading ? (
            <Spinner label="Loading grimoires…" />
          ) : books.length ? (
            <div className="grimoire-list">
              {books.map((grimoire) => (
                <GrimoireCard
                  key={grimoire.id}
                  grimoire={grimoire}
                  publicSlug={lib.public_slug}
                />
              ))}
            </div>
          ) : (
            <EmptyState title="No grimoires yet">
              <p>Add a book, then create its first folio.</p>
              <Button variant="primary" onClick={() => setCreateOpen(true)}>
                Create a grimoire
              </Button>
            </EmptyState>
          )}
        </section>

        <aside className="build-panel">
          <div className="section-head">
            <h2>Publishing</h2>
            <p className="muted">
              Builds are immutable snapshots. Publishing points latest and
              stable at a successful build.
            </p>
          </div>
          <Button
            variant="primary"
            className="button-block"
            onClick={() => build.mutate()}
            disabled={building || build.isPending || books.length === 0}
          >
            <IconRocket size={17} aria-hidden="true" />
            {building ? "Build in progress…" : "Build site"}
          </Button>
          {publication.data ? (
            <div className="channel-list">
              <div>
                <span className="channel-label">Latest</span>
                <span>
                  {publication.data.latest
                    ? `#${publication.data.latest.build_number}`
                    : "Not published"}
                </span>
              </div>
              <div>
                <span className="channel-label">Stable</span>
                <span>
                  {publication.data.stable
                    ? `#${publication.data.stable.build_number}`
                    : "Not published"}
                </span>
              </div>
            </div>
          ) : null}

          <div className="build-list">
            {builds.data?.length ? (
              builds.data
                .slice(0, 8)
                .map((row) => (
                  <BuildRow
                    key={row.id}
                    build={row}
                    athenaeum={lib}
                    onPublish={(buildId, channel) =>
                      setConfirmPublish({ buildId, channel })
                    }
                  />
                ))
            ) : (
              <p className="muted small">No builds yet.</p>
            )}
          </div>
        </aside>
      </div>

      <CreateGrimoireDialog
        athenaeumId={lib.id}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
      <SettingsDialog
        athenaeum={lib}
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
      <ConfirmDialog
        open={Boolean(confirmPublish)}
        onOpenChange={(open) => {
          if (!open) setConfirmPublish(null);
        }}
        title="Publish build"
        message="Publishing makes this immutable build available on the selected channel. Existing numbered URLs stay available."
        confirmLabel="Publish"
        busy={publish.isPending}
        onConfirm={() => {
          if (confirmPublish) publish.mutate(confirmPublish);
        }}
      />
    </div>
  );
}
