import type { JSONContent } from "@tiptap/core";

export interface User {
  id: string;
  email: string;
  display: string;
}

export interface Athenaeum {
  id: string;
  owner_id: string;
  slug: string;
  public_slug: string;
  title: string;
  is_public: boolean;
  latest_build_id: string | null;
  stable_build_id: string | null;
  custom_css_bytes: number;
  custom_css_sha256: string | null;
}

export interface Grimoire {
  id: string;
  athenaeum_id: string;
  slug: string;
  title: string;
  source_format: "rst" | "myst";
  theme: string;
  category_id: string | null;
  created_by: string | null;
  role: "owner" | "editor" | "viewer";
}

export interface TreeNode {
  id: string;
  parent_id: string | null;
  kind: "chapter" | "folio";
  title: string;
  slug: string;
  position: number;
  children: TreeNode[];
}

export interface TreeResponse {
  grimoire_id: string;
  nodes: TreeNode[];
}

export interface DocumentBody {
  node_id: string;
  version: number;
  tiptap_json: JSONContent;
  source_text: string;
  source_format: "rst" | "myst";
  updated_by: string | null;
  updated_at: string;
}

export interface HistoryEntry {
  version: number;
  author: string | null;
  at: string;
}

export interface HistoryResponse {
  document_id: string;
  versions: HistoryEntry[];
}

export interface HistoryVersion {
  document_id: string;
  version: number;
  tiptap_json: JSONContent;
  source_text: string;
  author: string | null;
  at: string;
}

export interface MediaAsset {
  id: string;
  grimoire_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  url: string;
  content_url: string;
  created_at: string;
}

export interface Build {
  id: string;
  athenaeum_id: string;
  build_number: number;
  status: "queued" | "running" | "ok" | "failed";
  triggered_by: string | null;
  started: string | null;
  finished: string | null;
  log_path: string | null;
  artifact_path: string | null;
  published_at: string | null;
  published_by: string | null;
}

export interface PublicationBuild {
  build_id: string;
  build_number: number;
  status: string;
  published_at: string | null;
  published_by: string | null;
  url: string;
}

export interface Publication {
  athenaeum_id: string;
  public_slug: string;
  public_aliases: { slug: string; retired_at: string | null }[];
  is_public: boolean;
  latest: PublicationBuild | null;
  stable: PublicationBuild | null;
  latest_url: string;
  stable_url: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
