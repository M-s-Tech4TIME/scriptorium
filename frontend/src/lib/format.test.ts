import { describe, expect, it } from "vitest";

import { formatDate, isSlug, slugify } from "./format";

describe("slugify", () => {
  it("normalizes accents, case, and punctuation", () => {
    expect(slugify("Café — Déjà Vu!")).toBe("cafe-deja-vu");
  });

  it("trims separators and bounds the result", () => {
    expect(slugify("  --Hello World--  ")).toBe("hello-world");
    expect(slugify("a".repeat(200))).toHaveLength(120);
  });
});

describe("isSlug", () => {
  it("accepts lowercase letters, digits, and hyphens only", () => {
    expect(isSlug("getting-started-2")).toBe(true);
    expect(isSlug("Getting Started")).toBe(false);
    expect(isSlug("under_score")).toBe(false);
    expect(isSlug("")).toBe(false);
  });
});

describe("formatDate", () => {
  it("renders an em dash for missing or invalid values", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("—");
  });

  it("formats valid ISO timestamps", () => {
    expect(formatDate("2026-10-31T12:00:00Z")).not.toBe("—");
  });
});
