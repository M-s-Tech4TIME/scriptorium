"""Search-core semantics, pinned in Node (0032 ③) — pure, offline.

The theme's one search mechanism ranks **heading-delimited sections**:
the whole typed sentence is a phrase bonus, every content word must be
able to contribute (OR-union candidates), the last token may match as a
prefix, every typed word is highlighted, and stopwords never create a
hit on their own. Those rules live in `scriptorium.js`; this test runs
that exact file in Node with a tiny DOM stub and a deterministic
stopword set/stemmer, so a regression in the scoring core fails the
backend suite without a browser.

Skipped only when Node is absent from the machine. GitHub's ubuntu
runners ship Node 24; the frozen stack lists Node 24 LTS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None, reason="Node is required to execute the theme search core"
)

JS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "sphinx"
    / "theme"
    / "scriptorium"
    / "static"
    / "scriptorium.js"
)

HARNESS = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

// values built inside the vm context have that realm's prototypes, so
// structural comparisons go through JSON
const same = (actual, expected, message) =>
  assert.equal(JSON.stringify(actual), JSON.stringify(expected), message);

const source = fs.readFileSync(process.env.SD_THEME_JS, "utf8");

const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  URLSearchParams,
  Map,
  Set,
  Promise,
  addEventListener: () => {},
  document: {
    querySelectorAll: () => [],
    querySelector: () => null,
    getElementById: () => null,
    addEventListener: () => {},
    head: { appendChild: () => {} },
    documentElement: { getAttribute: () => "" },
    body: { classList: { add: () => {}, remove: () => {} } },
  },
  navigator: {},
  Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 },
  DOMParser: function () {},
};
// the script reads the language pack from the global scope; the engine
// emits `window.Stemmer` and a global lexical `stopwords`
sandbox.stopwords = new Set([
  "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
  "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
  "were", "with",
]);
sandbox.Stemmer = function () {
  this.stemWord = (word) => word;
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const api = sandbox.__sdSearch;
assert.ok(api, "scriptorium.js must expose the search test seam");

// ---- planning: every typed word stays displayable ----------------------
const plan = api.planQuery("Inside the furnace the berserker");
same(plan.display, ["inside", "the", "furnace", "the", "berserker"]);
assert.equal(plan.phrase, "inside the furnace the berserker");
same(plan.scoring, ["inside", "furnace", "berserker"]);
assert.equal(plan.prefixWord, "berserker");
assert.ok(api.planQuery("").hasQuery === false);

// ---- the closest sentence wins ----------------------------------------
const phraseSection = {
  title: "Every Heading Level",
  text: "Inside the furnace the berserker incantation renders only by moonlight.",
};
const scattered = {
  title: "Furnace Rites",
  text: "The furnace breathes heat into the mold. A berserker note sits elsewhere.",
};
const phraseScore = api.scoreSection(plan, phraseSection);
const scatteredScore = api.scoreSection(plan, scattered);
assert.ok(phraseScore && scatteredScore);
assert.equal(phraseScore.phrase, true);
assert.ok(
  phraseScore.score > scatteredScore.score,
  `phrase ${phraseScore.score} must outrank scattered ${scatteredScore.score}`
);

// ---- stopwords are display words, not score words ----------------------
assert.equal(api.scoreSection(plan, { title: "", text: "the the the" }), null);

// ---- prefix matching is the LAST token only ----------------------------
const partial = api.planQuery("incant");
assert.equal(partial.prefixWord, "incant");
assert.ok(api.scoreSection(partial, { title: "", text: "Only an incantation remains." }));
const midword = api.planQuery("incant renders");
const midwordScore = api.scoreSection(midword, {
  title: "",
  text: "Incantation renders.",
});
assert.ok(midwordScore);
assert.equal(midwordScore.matched, 1, "only the last token may match as a prefix");

// ---- highlights: all typed words, whole-word boundaries ----------------
const segments = api.splitHighlight(
  "Inside the furnace, the berserker waits.",
  plan
);
assert.equal(
  segments.map((segment) => segment.text).join(""),
  "Inside the furnace, the berserker waits."
);
same(
  segments.filter((segment) => segment.hit).map((segment) => segment.text),
  ["Inside", "the", "furnace", "the", "berserker"]
);
const boundary = api.splitHighlight("There is a theme in the furnace.", plan);
same(
  boundary
    .filter((segment) => segment.hit)
    .map((segment) => segment.text.toLowerCase()),
  ["the", "furnace"],
  "the stopword must not light up inside There/theme"
);
const prefixHits = api.splitHighlight("An incantation remains.", partial);
same(
  prefixHits.filter((segment) => segment.hit).map((segment) => segment.text),
  ["incantation"]
);

// ---- snippet anchors on the sentence -----------------------------------
const snippet = api.bestSnippet(plan, phraseSection);
assert.ok(
  snippet.includes("Inside the furnace the berserker"),
  `snippet lost the phrase: ${snippet}`
);

// ---- the heading is scored once and never echoed in the snippet --------
assert.ok(plan.phraseRe.test("Inside the furnace the berserker"));
const bodySection = {
  title: "Furnace Rites",
  heading: "Furnace Rites",
  text: "Furnace Rites Inside the furnace the berserker waits.",
  body: "Inside the furnace the berserker waits.",
};
const bodySnippet = api.bestSnippet(plan, bodySection);
assert.ok(
  bodySnippet.startsWith("Inside the furnace the berserker"),
  `snippet must start at the section body, not repeat the heading: ${bodySnippet}`
);

// ---- punctuation-blind phrase -----------------------------------------
const punct = api.planQuery("furnace, berserker");
assert.ok(api.scoreSection(punct, {
  title: "",
  text: "The furnace, berserker, and mold.",
}));

console.log("search-core: ok");
"""


def test_search_core_semantics() -> None:
    assert NODE is not None  # narrowed for mypy; skipif already guards
    env = dict(os.environ)
    env["SD_THEME_JS"] = str(JS_PATH)
    result = subprocess.run(
        [NODE, "-e", HARNESS],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
