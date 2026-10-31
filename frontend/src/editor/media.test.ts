import type { JSONContent } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import {
  canonicalizeMedia,
  collectImageSources,
  mapImageSources,
  mediaAssetId,
  newMediaMaps,
  resolveMedia,
  revokeMedia,
} from "./media";

vi.mock("../api/client", () => ({
  api: { mediaBlob: vi.fn() },
}));

const ASSET = "11111111-2222-4333-8444-555555555555";
const MEDIA_URL = `/_static/media/${ASSET}.png`;

function docWithImages(...sources: string[]): JSONContent {
  return {
    type: "doc",
    content: sources.map((src) => ({
      type: "image",
      attrs: { src, alt: "dot" },
    })),
  };
}

describe("mediaAssetId", () => {
  it("recognizes canonical media URLs", () => {
    expect(mediaAssetId(MEDIA_URL)).toBe(ASSET);
    expect(mediaAssetId(`/_static/media/${ASSET}.gif`)).toBe(ASSET);
  });

  it("rejects external, blob, and malformed URLs", () => {
    expect(mediaAssetId("https://example.test/dot.png")).toBeNull();
    expect(mediaAssetId("blob:http://localhost/abc")).toBeNull();
    expect(mediaAssetId("/_static/media/not-a-uuid.png")).toBeNull();
    expect(mediaAssetId(`/_static/media/${ASSET}.svg`)).toBeNull();
  });
});

describe("mapImageSources", () => {
  it("rewrites nested image sources without mutating the input", () => {
    const source: JSONContent = {
      type: "doc",
      content: [
        {
          type: "blockquote",
          content: [docWithImages(MEDIA_URL).content![0]!],
        },
      ],
    };
    const mapped = mapImageSources(source, (src) => `blob:${src}`);
    expect(mapped.content?.[0]?.content?.[0]?.attrs?.src).toBe(
      `blob:${MEDIA_URL}`,
    );
    expect(source.content?.[0]?.content?.[0]?.attrs?.src).toBe(MEDIA_URL);
  });

  it("leaves non-image nodes and missing sources untouched", () => {
    const source: JSONContent = {
      type: "doc",
      content: [{ type: "paragraph" }, { type: "image", attrs: {} }],
    };
    expect(mapImageSources(source, () => "changed")).toEqual(source);
  });
});

describe("collectImageSources", () => {
  it("deduplicates sources across the document", () => {
    expect(
      collectImageSources(
        docWithImages(MEDIA_URL, MEDIA_URL, `/_static/media/${ASSET}.webp`),
      ),
    ).toEqual([MEDIA_URL, `/_static/media/${ASSET}.webp`]);
  });
});

describe("resolveMedia and canonicalizeMedia", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:asset"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("resolves canonical URLs to blob URLs and back", async () => {
    vi.mocked(api.mediaBlob).mockResolvedValue(new Blob(["png"]));
    const maps = newMediaMaps();
    const resolved = await resolveMedia(docWithImages(MEDIA_URL), maps);
    expect(resolved.content?.[0]?.attrs?.src).toBe("blob:asset");
    expect(api.mediaBlob).toHaveBeenCalledWith(ASSET);
    expect(canonicalizeMedia(resolved, maps).content?.[0]?.attrs?.src).toBe(
      MEDIA_URL,
    );
    revokeMedia(maps);
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:asset");
  });

  it("keeps canonical URLs when the asset cannot be loaded", async () => {
    vi.mocked(api.mediaBlob).mockRejectedValue(new Error("missing"));
    const maps = newMediaMaps();
    const resolved = await resolveMedia(docWithImages(MEDIA_URL), maps);
    expect(resolved.content?.[0]?.attrs?.src).toBe(MEDIA_URL);
  });

  it("does not refetch sources already mapped", async () => {
    vi.mocked(api.mediaBlob).mockResolvedValue(new Blob(["png"]));
    const maps = newMediaMaps();
    await resolveMedia(docWithImages(MEDIA_URL), maps);
    await resolveMedia(docWithImages(MEDIA_URL), maps);
    expect(api.mediaBlob).toHaveBeenCalledTimes(1);
  });
});
