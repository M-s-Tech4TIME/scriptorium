import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, setAccessToken } from "./client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
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
