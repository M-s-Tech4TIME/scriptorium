import type {
  Athenaeum,
  Build,
  DocumentBody,
  Grimoire,
  HistoryResponse,
  HistoryVersion,
  LoginResponse,
  MediaAsset,
  Publication,
  TreeNode,
  TreeResponse,
  User,
} from "./types";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

function detailMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return String(item);
      })
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // non-JSON error body
  }
  return new ApiError(
    response.status,
    detailMessage(payload, `Request failed (${response.status}).`),
  );
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_ROOT}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        accessToken = null;
        return null;
      }
      const body = (await response.json()) as LoginResponse;
      accessToken = body.access_token;
      return accessToken;
    } catch {
      accessToken = null;
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  rawBody?: BodyInit;
  headers?: Record<string, string>;
  retryAuth?: boolean;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    rawBody,
    headers = {},
    retryAuth = true,
  } = options;
  const requestHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };
  if (accessToken) requestHeaders.Authorization = `Bearer ${accessToken}`;

  let payload: BodyInit | undefined = rawBody;
  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    method,
    headers: requestHeaders,
    body: payload,
    credentials: "include",
  });

  if (response.status === 401 && retryAuth && !path.startsWith("/auth/login")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, { ...options, retryAuth: false });
    }
  }

  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const body = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      retryAuth: false,
    });
    accessToken = body.access_token;
    return body;
  },

  async refresh(): Promise<string | null> {
    return refreshAccessToken();
  },

  async logout(): Promise<void> {
    try {
      await request<void>("/auth/logout", { method: "POST", retryAuth: false });
    } finally {
      accessToken = null;
    }
  },

  me(): Promise<User> {
    return request<User>("/auth/me");
  },

  listAthenaeums(): Promise<Athenaeum[]> {
    return request<Athenaeum[]>("/athenaeums");
  },

  getAthenaeum(id: string): Promise<Athenaeum> {
    return request<Athenaeum>(`/athenaeums/${id}`);
  },

  createAthenaeum(input: { slug: string; title: string }): Promise<Athenaeum> {
    return request<Athenaeum>("/athenaeums", { method: "POST", body: input });
  },

  patchAthenaeum(
    id: string,
    input: Partial<Pick<Athenaeum, "title" | "slug" | "is_public">>,
  ): Promise<Athenaeum> {
    return request<Athenaeum>(`/athenaeums/${id}`, {
      method: "PATCH",
      body: input,
    });
  },

  renamePublicSlug(id: string, publicSlug: string): Promise<Athenaeum> {
    return request<Athenaeum>(`/athenaeums/${id}/public-slug`, {
      method: "PATCH",
      body: { public_slug: publicSlug },
    });
  },

  listGrimoires(): Promise<Grimoire[]> {
    return request<Grimoire[]>("/grimoires");
  },

  getGrimoire(id: string): Promise<Grimoire> {
    return request<Grimoire>(`/grimoires/${id}`);
  },

  createGrimoire(input: {
    athenaeum_id: string;
    slug: string;
    title: string;
    source_format: "rst" | "myst";
  }): Promise<Grimoire> {
    return request<Grimoire>("/grimoires", { method: "POST", body: input });
  },

  patchGrimoire(
    id: string,
    input: Partial<Pick<Grimoire, "title" | "slug">>,
  ): Promise<Grimoire> {
    return request<Grimoire>(`/grimoires/${id}`, {
      method: "PATCH",
      body: input,
    });
  },

  deleteGrimoire(id: string): Promise<void> {
    return request<void>(`/grimoires/${id}`, { method: "DELETE" });
  },

  getTree(grimoireId: string): Promise<TreeResponse> {
    return request<TreeResponse>(`/grimoires/${grimoireId}/tree`);
  },

  createNode(
    grimoireId: string,
    input: {
      parent_id?: string | null;
      kind: "chapter" | "folio";
      title: string;
      slug: string;
    },
  ): Promise<TreeNode> {
    return request<TreeNode>(`/grimoires/${grimoireId}/nodes`, {
      method: "POST",
      body: input,
    });
  },

  patchNode(
    grimoireId: string,
    nodeId: string,
    input: {
      title?: string;
      slug?: string;
      parent_id?: string | null;
      position?: number;
    },
  ): Promise<void> {
    return request<void>(`/grimoires/${grimoireId}/nodes/${nodeId}`, {
      method: "PATCH",
      body: input,
    });
  },

  deleteNode(grimoireId: string, nodeId: string): Promise<void> {
    return request<void>(`/grimoires/${grimoireId}/nodes/${nodeId}`, {
      method: "DELETE",
    });
  },

  getDocument(grimoireId: string, nodeId: string): Promise<DocumentBody> {
    return request<DocumentBody>(
      `/grimoires/${grimoireId}/nodes/${nodeId}/document`,
    );
  },

  putDocument(
    grimoireId: string,
    nodeId: string,
    input: {
      tiptap_json?: unknown;
      source_text?: string;
      expected_version: number;
    },
  ): Promise<DocumentBody> {
    return request<DocumentBody>(
      `/grimoires/${grimoireId}/nodes/${nodeId}/document`,
      { method: "PUT", body: input },
    );
  },

  getHistory(grimoireId: string, nodeId: string): Promise<HistoryResponse> {
    return request<HistoryResponse>(
      `/grimoires/${grimoireId}/nodes/${nodeId}/document/history`,
    );
  },

  getHistoryVersion(
    grimoireId: string,
    nodeId: string,
    version: number,
  ): Promise<HistoryVersion> {
    return request<HistoryVersion>(
      `/grimoires/${grimoireId}/nodes/${nodeId}/document/history/${version}`,
    );
  },

  restoreHistory(
    grimoireId: string,
    nodeId: string,
    version: number,
    expectedVersion: number,
  ): Promise<DocumentBody> {
    return request<DocumentBody>(
      `/grimoires/${grimoireId}/nodes/${nodeId}/document/history/${version}/restore`,
      { method: "POST", body: { expected_version: expectedVersion } },
    );
  },

  uploadMedia(grimoireId: string, file: File): Promise<MediaAsset> {
    return request<MediaAsset>(
      `/grimoires/${grimoireId}/media?filename=${encodeURIComponent(file.name)}`,
      {
        method: "POST",
        rawBody: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      },
    );
  },

  async mediaBlob(assetId: string): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    let response = await fetch(`${API_ROOT}/media/${assetId}/content`, {
      headers,
      credentials: "include",
    });
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        response = await fetch(`${API_ROOT}/media/${assetId}/content`, {
          headers: { Authorization: `Bearer ${refreshed}` },
          credentials: "include",
        });
      }
    }
    if (!response.ok) throw await parseError(response);
    return response.blob();
  },

  listBuilds(athenaeumId: string): Promise<Build[]> {
    return request<Build[]>(`/athenaeums/${athenaeumId}/builds`);
  },

  triggerBuild(athenaeumId: string): Promise<Build> {
    return request<Build>(`/athenaeums/${athenaeumId}/builds`, {
      method: "POST",
    });
  },

  getPublication(athenaeumId: string): Promise<Publication> {
    return request<Publication>(`/athenaeums/${athenaeumId}/publication`);
  },

  publish(
    athenaeumId: string,
    buildId: string,
    channel: "latest" | "stable" | "both",
  ): Promise<Publication> {
    return request<Publication>(`/athenaeums/${athenaeumId}/publish`, {
      method: "POST",
      body: { build_id: buildId, channel },
    });
  },
};
