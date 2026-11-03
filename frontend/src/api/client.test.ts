import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, setAccessToken } from "./client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function backupJob(overrides: Record<string, unknown> = {}): unknown {
  return {
    id: "job-1",
    kind: "export",
    athenaeum_id: "a1",
    result_athenaeum_id: null,
    mode: "full",
    format: "tar.gz",
    status: "queued",
    size_bytes: null,
    sha256: null,
    error: null,
    created_at: "2026-11-01T00:00:00Z",
    started_at: null,
    finished_at: null,
    expires_at: null,
    downloaded_at: null,
    download_url: null,
    ...overrides,
  };
}

describe("api client auth", () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps the access token from login and sends it as a bearer", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        json({ access_token: "access-1", token_type: "bearer" }),
      )
      .mockResolvedValueOnce(
        json({ id: "u1", email: "me@example.test", display: "Me" }),
      );

    await api.login("me@example.test", "secret");
    const me = await api.me();

    expect(me.email).toBe("me@example.test");
    const second = fetchMock.mock.calls[1];
    expect(second?.[0]).toBe("/api/v1/auth/me");
    expect((second?.[1]?.headers as Record<string, string>).Authorization).toBe(
      "Bearer access-1",
    );
  });

  it("refreshes once and retries the original request after a 401", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(json({ detail: "expired" }, 401))
      .mockResolvedValueOnce(
        json({ access_token: "access-2", token_type: "bearer" }),
      )
      .mockResolvedValueOnce(
        json({ id: "u1", email: "me@example.test", display: "Me" }),
      );

    const me = await api.me();

    expect(me.id).toBe("u1");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/auth/refresh");
    const retried = fetchMock.mock.calls[2];
    expect(
      (retried?.[1]?.headers as Record<string, string>).Authorization,
    ).toBe("Bearer access-2");
  });

  it("surfaces FastAPI validation details as ApiError", async () => {
    vi.mocked(fetch).mockResolvedValue(
      json({ detail: [{ msg: "field required" }, { msg: "bad slug" }] }, 422),
    );

    await expect(api.listAthenaeums()).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        status: 422,
        message: "field required; bad slug",
      }),
    );
    await expect(api.listAthenaeums()).rejects.toBeInstanceOf(ApiError);
  });
});

describe("api client backups", () => {
  beforeEach(() => {
    setAccessToken("access-1");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("streams an Editorial export as a named blob with its digest", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response("archive-bytes", {
        status: 200,
        headers: {
          "Content-Type": "application/zip",
          "Content-Disposition":
            'attachment; filename="scriptorium-library-editorial.zip"',
          "X-Backup-SHA256": "abc123",
          "X-Backup-Size": "13",
        },
      }),
    );

    const result = await api.exportBackup("a1", "editorial", "zip");

    if (!("blob" in result)) throw new Error("expected a streamed archive");
    expect(await result.blob.text()).toBe("archive-bytes");
    expect(result.filename).toBe("scriptorium-library-editorial.zip");
    expect(result.sha256).toBe("abc123");
    expect(result.size_bytes).toBe(13);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/athenaeums/a1/backups");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(
      JSON.stringify({ mode: "editorial", format: "zip" }),
    );
    expect((init?.headers as Record<string, string>).Authorization).toBe(
      "Bearer access-1",
    );
  });

  it("returns the queued job for a Full export", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(json(backupJob(), 202));

    const result = await api.exportBackup("a1", "full", "tar.gz");

    if ("blob" in result) throw new Error("expected a backup job");
    expect(result.kind).toBe("export");
    expect(result.status).toBe("queued");
    expect(result.mode).toBe("full");
  });

  it("posts a restore archive and distinguishes jobs from results", async () => {
    const file = new File(["archive"], "backup.zip", {
      type: "application/zip",
    });
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        json(
          backupJob({
            kind: "restore",
            result_athenaeum_id: "a2",
            status: "ok",
          }),
          202,
        ),
      )
      .mockResolvedValueOnce(
        json(
          {
            athenaeum_id: "a3",
            title: "Restored library",
            public_slug: "restored-library",
            mode: "editorial",
            warnings: [],
            counts: { builds: 2 },
          },
          201,
        ),
      );

    const job = await api.restoreBackup(file);
    if ("public_slug" in job) throw new Error("expected a restore job");
    expect(job.kind).toBe("restore");
    expect(job.result_athenaeum_id).toBe("a2");

    const result = await api.restoreBackup(file);
    if (!("public_slug" in result))
      throw new Error("expected a restore result");
    expect(result.athenaeum_id).toBe("a3");
    expect(result.counts.builds).toBe(2);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/backups/restore");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(file);
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/zip",
    );
  });
});
