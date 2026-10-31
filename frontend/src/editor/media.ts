import type { JSONContent } from "@tiptap/core";

import { api } from "../api/client";

const MEDIA_RE =
  /^\/_static\/media\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(png|jpe?g|gif|webp|avif)$/;

export interface MediaMaps {
  canonicalToBlob: Map<string, string>;
  blobToCanonical: Map<string, string>;
}

export function newMediaMaps(): MediaMaps {
  return { canonicalToBlob: new Map(), blobToCanonical: new Map() };
}

export function mediaAssetId(src: string): string | null {
  const match = MEDIA_RE.exec(src);
  return match?.[1] ?? null;
}

export function mapImageSources(
  node: JSONContent,
  transform: (src: string) => string,
): JSONContent {
  if (node.type === "image") {
    const attrs = node.attrs ?? {};
    const src = attrs.src;
    if (typeof src === "string") {
      return { ...node, attrs: { ...attrs, src: transform(src) } };
    }
    return node;
  }
  if (!node.content) return node;
  return {
    ...node,
    content: node.content.map((child) => mapImageSources(child, transform)),
  };
}

export function collectImageSources(node: JSONContent): string[] {
  const found = new Set<string>();
  const walk = (current: JSONContent) => {
    if (current.type === "image") {
      const src = current.attrs?.src;
      if (typeof src === "string") found.add(src);
    }
    current.content?.forEach(walk);
  };
  walk(node);
  return [...found];
}

export async function resolveMedia(
  content: JSONContent,
  maps: MediaMaps,
): Promise<JSONContent> {
  const sources = collectImageSources(content).filter(
    (src) => !maps.canonicalToBlob.has(src),
  );
  await Promise.all(
    sources.map(async (src) => {
      const assetId = mediaAssetId(src);
      if (!assetId) return;
      try {
        const blob = await api.mediaBlob(assetId);
        const blobUrl = URL.createObjectURL(blob);
        maps.canonicalToBlob.set(src, blobUrl);
        maps.blobToCanonical.set(blobUrl, src);
      } catch {
        // A missing asset leaves the canonical URL in place; saving keeps it.
      }
    }),
  );
  return mapImageSources(
    content,
    (src) => maps.canonicalToBlob.get(src) ?? src,
  );
}

export function canonicalizeMedia(
  content: JSONContent,
  maps: MediaMaps,
): JSONContent {
  return mapImageSources(
    content,
    (src) => maps.blobToCanonical.get(src) ?? src,
  );
}

export function revokeMedia(maps: MediaMaps): void {
  for (const blobUrl of maps.canonicalToBlob.values()) {
    URL.revokeObjectURL(blobUrl);
  }
  maps.canonicalToBlob.clear();
  maps.blobToCanonical.clear();
}
