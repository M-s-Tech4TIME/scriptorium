/* Scriptorium theme support script — M4-C3.5/0029, amended 0030–0032.
   The ONE first-party script the artifact carries (0027 JS clause as
   amended). Zero dependencies, zero network (all retrieval is
   same-origin, from the artifact itself):

     1. code-block chrome — header bar with the language badge and the
        always-visible copy button; on SUCCESS the icon flips to the
        green check (0031 ②) and back after a beat;
     2. the ONE search mechanism (0032 ①②③) — a shared query core used
        identically by the dialog and the full search page:
          · every typed word is searched (OR-union candidates over the
            engine's build-emitted `searchindex.js` as a fast pre-filter;
            stopwords are display/highlight words, not score words);
          · the WHOLE typed sentence is matched as a phrase and floats
            to the top ("closest sentence first");
          · candidate folios are retrieved same-origin, split into
            heading-delimited SECTIONS, and every matching section becomes
            a result row (heading + highlighted snippet) under its folio;
          · every typed word is marked in the snippet (including
            stopwords); the last token additionally matches as a prefix
            (RTD's partial-word behaviour);
          · rows carry the grimoire chip (book icon + grimoire name) as
            their bottom reference — the island contract is `{"books": …}`
            (0032 ① fixed the raw-map read that emptied every chip);
          · dialog: vertically centred, compact until results arrive,
            then grows to a capped height with internal scrolling; esc /
            backdrop / the Tabler x close button; ↑/↓/Enter keyboard bar;
            "Full results page" carries the query (`search.html?q=`).
        The full page renders the same rows on paper and pre-fills `?q=`;
        the engine's page-level `searchtools.js` flow is gone (0032 ②).
     3. On-This-Page scrollspy (0031 7.v rewrite, 0032 ⑨ title fix) — the
        last heading above the viewport stays active WHILE its section is
        being read; the page-title entry (`href="#"`) is included;
        clicking an anchor activates it immediately;
     4. panel collapse (0031 7.viii, 0032 ⑧ placement) — the collapse
        control lives beside the panel search field; when the panel is
        off, an expand control is the top-left-most thing in the top bar;
        state persists per device;
     5. the panel field's own clear control — the Tabler x (0032 ④)
        clears without opening the dialog (the native search-field clear
        used to bubble into the dialog trigger);
     6. nothing else.

   Offline character (disclosed in 0029/0031/0032): with an http/https-
   served artifact sections/snippets resolve in full; on a plain file://
   preview the browser blocks the same-origin retrieval, so rows degrade
   to folio/heading links without snippets. */

"use strict";

(function () {
  /* ================================================================ */
  /* Shared: content root, grimoire island, page retrieval cache      */
  /* ================================================================ */

  var MAX_CANDIDATE_DOCS = 10;
  var MAX_GROUPS = 8;
  var MAX_ROWS_PER_GROUP = 6;

  function contentRoot() {
    return document.documentElement.getAttribute("data-content_root") || "";
  }

  /** The `#sd-map` island → `{slug: {label, title}}` (0032 ①). */
  function readMap() {
    var node = document.getElementById("sd-map");
    if (!node) return {};
    var data = null;
    try {
      data = JSON.parse(node.textContent);
    } catch (err) {
      return {};
    }
    if (!data || typeof data !== "object") return {};
    if (data.books && typeof data.books === "object") return data.books;
    return data; // tolerate the pre-0032 raw map (no name regression)
  }

  var domCache = new Map();

  function fetchPage(url) {
    if (!domCache.has(url)) {
      domCache.set(
        url,
        fetch(url)
          .then(function (response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.text();
          })
          .then(function (text) {
            return new DOMParser().parseFromString(text, "text/html");
          })
          .catch(function () {
            // file:// preview: browsers block the retrieval — degrade
            return null;
          })
      );
    }
    return domCache.get(url);
  }

  /* ================================================================ */
  /* 1. Code-block chrome (language badge + copy button + check)      */
  /* ================================================================ */

  var LANG_NAMES = {
    python: "Python",
    javascript: "JavaScript",
    typescript: "TypeScript",
    html: "HTML",
    css: "CSS",
    json: "JSON",
    bash: "Bash",
    shell: "Shell",
    rst: "reStructuredText",
    myst: "MyST",
    markdown: "Markdown",
  };

  /** Lexer alias → display label. No language/default → "Code" (0034). */
  function languageFromClass(className) {
    var match = /(?:^|\s)highlight-([^\s]+)/.exec(className || "");
    if (!match) return "Code";
    var raw = match[1];
    if (raw === "default" || raw === "none" || raw === "text") return "Code";
    return (
      LANG_NAMES[raw] ||
      raw.charAt(0).toUpperCase() + raw.slice(1).replace(/-+/g, " ")
    );
  }

  function languageName(block) {
    // 0034: the lexer class is on the OUTER `div.highlight-<lang>`; the
    // block itself is the inner `div.highlight`. `closest` must skip the
    // inner block (the old `[class*=highlight]` matched it and returned
    // an empty label for every code block).
    var holder = block.closest("[class*='highlight-']") || block;
    return languageFromClass(holder.className || "");
  }

  var COPY_ICON = "#sd-i-copy";
  var CHECK_ICON = "#sd-i-check";

  function copiedState(button) {
    button.classList.add("sd-copied");
    var use = button.querySelector("use");
    if (use) use.setAttribute("href", CHECK_ICON);
    window.setTimeout(function () {
      button.classList.remove("sd-copied");
      if (use) use.setAttribute("href", COPY_ICON);
    }, 1600);
  }

  function fallbackCopy(text) {
    // non-secure-context path; kept tiny — file:// IS a secure context
    var scratch = document.createElement("textarea");
    scratch.value = text;
    scratch.setAttribute("readonly", "");
    scratch.style.position = "absolute";
    scratch.style.left = "-9999px";
    document.body.appendChild(scratch);
    scratch.select();
    try {
      document.execCommand("copy");
    } finally {
      document.body.removeChild(scratch);
    }
  }

  function copyText(text, button) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(function () {
          copiedState(button);
        })
        .catch(function () {
          fallbackCopy(text);
          copiedState(button);
        });
    } else {
      fallbackCopy(text);
      copiedState(button);
    }
  }

  function wireCodeBlock(block) {
    if (block.querySelector(".sd-cb-head")) return; // idempotent
    var head = document.createElement("div");
    head.className = "sd-cb-head";
    head.innerHTML =
      '<span class="sd-cb-lang"><svg class="sd-icon" aria-hidden="true">' +
      '<use href="#sd-i-code"></use></svg><span></span></span>' +
      '<button type="button" class="sd-copy" aria-label="Copy code" title="Copy code">' +
      '<svg class="sd-icon" aria-hidden="true"><use href="' + COPY_ICON + '"></use></svg>' +
      "</button>";
    head.querySelector(".sd-cb-lang > span").textContent = languageName(block);
    block.classList.add("sd-cb");
    block.insertBefore(head, block.firstChild);

    var button = head.querySelector(".sd-copy");
    var pre = block.querySelector("pre");
    button.addEventListener("click", function () {
      copyText(pre ? pre.textContent : "", button);
    });
  }

  /* ================================================================ */
  /* 2. Search language + index loaders                               */
  /* ================================================================ */

  var packPromise = null; // language pack: stopwords/Stemmer
  var INDEX = null; // the build-emitted search index

  function injectScript(src, onload, onerror) {
    var node = document.createElement("script");
    node.src = src;
    node.onload = onload;
    node.onerror = onerror;
    document.head.appendChild(node);
  }

  /* `language_data.js` is self-contained (stopwords + base stemmer +
     the language stemmer). It must not EXECUTE twice — the search page
     already loads it. NOTE: `splitQuery` lives in the engine's
     `searchtools.js` in 9.1 — NOT here; the core splits with its own
     inline match of the engine's default word class. */
  function loadLanguagePack() {
    if (packPromise) return packPromise;
    packPromise = new Promise(function (resolve, reject) {
      var ready = function () {
        resolve(
          typeof Stemmer === "function" &&
            typeof stopwords !== "undefined"
        );
      };
      if (document.querySelector('script[src*="language_data"]')) ready();
      else {
        injectScript(
          contentRoot() + "_static/language_data.js",
          ready,
          function () {
            reject(new Error("language pack failed"));
          }
        );
      }
    }).then(function (ok) {
      if (!ok) throw new Error("language pack incomplete");
      return ok;
    });
    return packPromise;
  }

  /* The build-emitted `searchindex.js` calls `Search.setIndex(data)`.
     The engine's own `Search` object is not on the page (0032 removed
     the searchtools flow), so a minimal shim of the engine's own loader
     contract holds the data and we inject/await the index ourselves. */
  function loadIndex() {
    return loadLanguagePack().then(function () {
      return new Promise(function (resolve, reject) {
        if (INDEX) return resolve(INDEX);
        INDEX = window.__sdScriptoriumIndex || (window.Search && Search._index);
        if (INDEX) return resolve(INDEX);
        if (!window.Search) {
          window.Search = {
            setIndex: function (obj) {
              window.__sdScriptoriumIndex = obj;
            },
          };
        }
        var tag = document.querySelector('script[src*="searchindex"]');
        if (tag) {
          var tries = 0;
          (function poll() {
            INDEX = window.__sdScriptoriumIndex || (window.Search && Search._index);
            if (INDEX) return resolve(INDEX);
            if (tries > 80) return reject(new Error("search index unavailable"));
            tries += 1;
            window.setTimeout(poll, 50);
          })();
          return undefined;
        }
        injectScript(
          contentRoot() + "searchindex.js",
          function () {
            INDEX = window.__sdScriptoriumIndex || (window.Search && Search._index);
            if (INDEX) resolve(INDEX);
            else reject(new Error("search index unavailable"));
          },
          function () {
            reject(new Error("search index failed"));
          }
        );
      });
    });
  }

  /* ================================================================ */
  /* 3. Search core — query plan, candidates, sections, scoring       */
  /* ================================================================ */

  function asArr(value) {
    if (value == null) return [];
    if (value.length === undefined) return [value];
    return Array.prototype.filter.call(value, function (n) {
      return n !== undefined;
    });
  }

  function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  /* the engine's 9.1 default word class (its own default splitQuery
     regex, packaged directly): split on everything that is not a
     letter/number/underscore/emoji-presentation char. */
  function splitWords(text) {
    return text.trim().match(/[\p{Letter}\p{Number}_\p{Emoji_Presentation}]+/gu) || [];
  }

  function isStopword(word) {
    return typeof stopwords !== "undefined" && stopwords.has(word);
  }

  /** "-word" exclusions are stripped before tokenizing (0032 keeps 0031's
      exclusion clause); returned lowercased for stemming. */
  function splitExclusions(text) {
    var excluded = [];
    var cleaned = text.replace(
      /(^|\s)-([\p{Letter}\p{Number}_\p{Emoji_Presentation}]+)/gu,
      function (match, before, word) {
        excluded.push(word.toLowerCase());
        return before;
      }
    );
    return { cleaned: cleaned, excluded: excluded };
  }

  function uniquePush(list, value) {
    if (value && list.indexOf(value) === -1) list.push(value);
  }

  /**
   * The whole query as one plan. `display` carries every typed word
   * (lowercase, for highlighting); `scoring` drops stopwords/numbers
   * (falling back to all words when the query is stopwords only);
   * `phrase` is the full typed sentence, in order; `prefixWord` is the
   * last content word when the user is mid-word (prefix matching).
   */
  function planQuery(query) {
    var raw = String(query == null ? "" : query);
    var parts = splitExclusions(raw);
    var words = splitWords(parts.cleaned);
    // display keeps EVERY typed word in order — the phrase must stay the
    // sentence the owner typed, including repeated stopwords
    var display = words.map(function (word) {
      return word.toLowerCase();
    });
    var content = [];
    display.forEach(function (word) {
      if (!isStopword(word) && !/^\d+$/.test(word)) uniquePush(content, word);
    });
    if (!content.length) {
      display.forEach(function (word) {
        if (!/^\d+$/.test(word)) uniquePush(content, word);
      });
    }
    var last = display.length ? display[display.length - 1] : "";
    var prefixWord =
      last && content.indexOf(last) !== -1 && last.length >= 3 ? last : "";
    var stemmer = new Stemmer();
    var terms = [];
    var seen = {};
    content.forEach(function (word) {
      var stem = stemmer.stemWord(word);
      if (seen[stem]) return;
      seen[stem] = true;
      terms.push({ word: word, stem: stem, prefix: word === prefixWord });
    });
    return {
      raw: raw.trim(),
      display: display,
      scoring: content,
      terms: terms,
      exclusions: parts.excluded.map(function (word) {
        return stemmer.stemWord(word);
      }),
      phrase: display.join(" "),
      phraseRe: phrasePattern(display.join(" ")),
      last: last,
      prefixWord: prefixWord,
      hasQuery: display.length > 0,
    };
  }

  /** Word-boundary matcher; prefix mode accepts the rest of a word. */
  function wordPattern(word, allowPrefix) {
    return (
      "(?<![\\p{Letter}\\p{N}_])" +
      escapeRegExp(word) +
      (allowPrefix ? "[\\p{Letter}\\p{N}_]*" : "") +
      "(?![\\p{Letter}\\p{N}_])"
    );
  }

  function countMatches(text, word, allowPrefix) {
    if (!text) return 0;
    var re = new RegExp(wordPattern(word, allowPrefix), "giu");
    return (text.match(re) || []).length;
  }

  /** The typed sentence as one phrase: words in order, punctuation-blind. */
  function phrasePattern(phrase) {
    if (!phrase) return null;
    var parts = phrase.split(" ").map(escapeRegExp);
    return new RegExp(
      "(?<![\\p{Letter}\\p{N}_])" +
        parts.join("[^\\p{Letter}\\p{N}_]+") +
        "(?![\\p{Letter}\\p{N}_])",
      "iu"
    );
  }

  /**
   * Score one heading-delimited section. Returns null when no scoring
   * word is present. Phrase hits dominate, then distinct-word coverage,
   * term frequency, and heading hits.
   */
  function scoreSection(plan, section) {
    // body = own section text WITHOUT the heading (the title is scored
    // separately, so a heading hit never counts twice)
    var text =
      (section && (section.body !== undefined ? section.body : section.text)) || "";
    var title = (section && section.title) || "";
    var matched = 0;
    var total = 0;
    var titleHits = 0;
    plan.scoring.forEach(function (word) {
      var allow = word === plan.prefixWord;
      var hits = countMatches(text, word, allow);
      if (hits) {
        matched += 1;
        total += hits;
      }
      if (countMatches(title, word, allow)) titleHits += 1;
    });
    if (!matched) return null;
    var phrase = plan.phraseRe || phrasePattern(plan.phrase);
    var phraseHit = phrase ? phrase.test(text) : false;
    var score = phraseHit ? 1000 : 0;
    score += matched * 40 + Math.min(total, 6) * 5 + titleHits * 60;
    if (matched === plan.scoring.length) score += 30;
    return { score: score, matched: matched, phrase: phraseHit };
  }

  /** Highlight segments: every typed word, case-insensitive, last token
      prefix-aware. Returns `[{text, hit}]` (DOM-free, testable). */
  function splitHighlight(text, plan) {
    var words = [];
    plan.display.forEach(function (word) {
      uniquePush(words, word);
    });
    words.sort(function (a, b) {
      return b.length - a.length;
    });
    var source = String(text == null ? "" : text);
    if (!words.length) return [{ text: source, hit: false }];
    var alts = words.map(function (word) {
      return (
        escapeRegExp(word) +
        (word === plan.prefixWord ? "[\\p{Letter}\\p{N}_]*" : "")
      );
    });
    var re = new RegExp(
      "(?<![\\p{Letter}\\p{N}_])(?:" + alts.join("|") + ")(?![\\p{Letter}\\p{N}_])",
      "giu"
    );
    var out = [];
    var last = 0;
    var match;
    while ((match = re.exec(source))) {
      if (match.index > last) {
        out.push({ text: source.slice(last, match.index), hit: false });
      }
      out.push({ text: match[0], hit: true });
      last = match.index + match[0].length;
      if (re.lastIndex === match.index) re.lastIndex += 1;
    }
    if (last < source.length) out.push({ text: source.slice(last), hit: false });
    return out;
  }

  /** A window around the phrase (preferred) or the longest words. */
  function bestSnippet(plan, section) {
    var source =
      (section && (section.body !== undefined ? section.body : section.text)) || "";
    var clean = source.replace(/\s+/g, " ").trim();
    if (!clean) return "";
    var lower = clean.toLowerCase();
    var at = -1;
    var phrase = plan.phraseRe || phrasePattern(plan.phrase);
    if (phrase) {
      var found = phrase.exec(clean);
      if (found) at = found.index;
    }
    if (at === -1) {
      var words = plan.scoring.slice().sort(function (a, b) {
        return b.length - a.length;
      });
      for (var i = 0; i < words.length; i += 1) {
        var re = new RegExp(
          wordPattern(words[i], words[i] === plan.prefixWord),
          "iu"
        );
        var hit = re.exec(clean);
        if (hit) {
          at = hit.index;
          break;
        }
      }
    }
    if (at === -1) at = 0;
    var start = Math.max(0, at - 60);
    var end = Math.min(clean.length, start + 220);
    if (start > 0) {
      var nextSpace = clean.indexOf(" ", start);
      start = nextSpace === -1 ? start : nextSpace + 1;
    }
    if (end < clean.length) {
      var prevSpace = clean.lastIndexOf(" ", end);
      if (prevSpace > start) end = prevSpace;
    }
    var snippet = clean.slice(start, end);
    if (start > 0) snippet = "\u2026 " + snippet;
    if (end < clean.length) snippet += " \u2026";
    return snippet;
  }

  /** Docs tied to the index pool; exact stem wins, otherwise a guarded
      prefix scan (the RTD partial-word path). */
  function poolHits(word, pool) {
    var out = {};
    if (!pool) return out;
    if (Object.prototype.hasOwnProperty.call(pool, word)) {
      asArr(pool[word]).forEach(function (doc) {
        out[doc] = Math.max(out[doc] || 0, 1);
      });
      return out;
    }
    if (word.length < 3) return out;
    Object.keys(pool).forEach(function (term) {
      if (term.length < 3) return;
      if (term.indexOf(word) !== 0 && word.indexOf(term) !== 0) return;
      asArr(pool[term]).forEach(function (doc) {
        out[doc] = Math.max(out[doc] || 0, 0.45);
      });
    });
    return out;
  }

  function isStructuralDoc(docname) {
    // masters + the site landing are hierarchy holders, not reading pages
    return docname === "index" || /(^|\/)index$/.test(docname);
  }

  /** OR-union over every scored term, title hits weighted; rarest first
      is approximated by the summed weight. */
  function candidateDocs(plan, idx) {
    var perDoc = {};
    var weights = [
      ["titleterms", 3],
      ["terms", 1],
    ];
    plan.terms.forEach(function (term) {
      weights.forEach(function (pair) {
        var hits = poolHits(term.stem, idx[pair[0]] || {});
        Object.keys(hits).forEach(function (doc) {
          perDoc[doc] = (perDoc[doc] || 0) + hits[doc] * pair[1];
        });
      });
    });
    var excluded = {};
    plan.exclusions.forEach(function (stem) {
      var hits = poolHits(stem, idx.terms || {});
      Object.keys(hits).forEach(function (doc) {
        excluded[doc] = true;
      });
    });
    var list = [];
    Object.keys(perDoc).forEach(function (doc) {
      var name = idx.docnames[doc];
      if (name === undefined || isStructuralDoc(name)) return;
      if (excluded[doc]) return;
      list.push({ doc: Number(doc), pre: perDoc[doc] });
    });
    list.sort(function (a, b) {
      return b.pre - a.pre || a.doc - b.doc;
    });
    return list.slice(0, MAX_CANDIDATE_DOCS);
  }

  /* ---------------- page section extraction ---------------- */

  function headingOf(section) {
    var kids = section.children;
    for (var i = 0; i < kids.length; i += 1) {
      if (/^H[1-6]$/.test(kids[i].tagName)) return kids[i];
    }
    return null;
  }

  function headingText(heading) {
    return (heading.textContent || "").replace(/\u00b6\s*$/, "").trim();
  }

  function collectOwnText(node, out) {
    var kids = node.childNodes;
    for (var i = 0; i < kids.length; i += 1) {
      var child = kids[i];
      if (child.nodeType === Node.TEXT_NODE) {
        var value = child.nodeValue || "";
        if (value.trim()) out.push(value.trim());
        continue;
      }
      if (child.nodeType !== Node.ELEMENT_NODE) continue;
      var tag = child.tagName.toLowerCase();
      if (tag === "section" || tag === "script" || tag === "style" || tag === "nav") {
        continue;
      }
      if (child.classList && child.classList.contains("headerlink")) continue;
      collectOwnText(child, out);
    }
  }

  /** Heading-delimited sections in reading order, with their chain. */
  function collectSections(box) {
    var nodes = box.querySelectorAll("section[id]");
    var sections = [];
    nodes.forEach(function (node) {
      var heading = headingOf(node);
      var chain = [];
      var walk = node.parentElement
        ? node.parentElement.closest("section[id]")
        : null;
      while (walk) {
        var parentHeading = headingOf(walk);
        if (parentHeading) chain.unshift(headingText(parentHeading));
        walk = walk.parentElement
          ? walk.parentElement.closest("section[id]")
          : null;
      }
      var pieces = [];
      collectOwnText(node, pieces);
      var full = pieces.join(" ");
      var headingLabel = heading ? headingText(heading) : "";
      var body = full;
      if (headingLabel && body.indexOf(headingLabel) === 0) {
        body = body.slice(headingLabel.length).trim();
      }
      sections.push({
        id: node.id || "",
        heading: headingLabel,
        chain: chain,
        text: full,
        body: body,
      });
    });
    if (!sections.length) {
      var top = box.querySelector("h1");
      var all = [];
      collectOwnText(box, all);
      var allText = all.join(" ");
      var topLabel = top ? headingText(top) : "";
      var allBody = allText;
      if (topLabel && allBody.indexOf(topLabel) === 0) {
        allBody = allBody.slice(topLabel.length).trim();
      }
      sections.push({
        id: top && top.parentElement ? top.parentElement.id || "" : "",
        heading: topLabel,
        chain: [],
        text: allText,
        body: allBody,
      });
    }
    return sections;
  }

  function fallbackDoc(plan, idx, docIdx) {
    // file:// preview (or a failed fetch): links without snippets (0031)
    var docname = idx.docnames[docIdx];
    var rows = [];
    var titles = idx.alltitles || {};
    Object.keys(titles).forEach(function (title) {
      var lower = title.toLowerCase();
      var hit = plan.scoring.some(function (word) {
        return lower.indexOf(word) !== -1;
      });
      if (!hit) return;
      asArr(titles[title]).forEach(function (location) {
        if (location[0] !== docIdx) return;
        rows.push({
          title: title,
          anchor: location[1] ? "#" + location[1] : "",
          chain: [],
          snippet: "",
          score: 10,
          order: rows.length,
        });
      });
    });
    if (!rows.length) {
      rows.push({
        title: idx.titles[docIdx] || docname,
        anchor: "",
        chain: [],
        snippet: "",
        score: 1,
        order: 0,
      });
    }
    return {
      docIdx: docIdx,
      docname: docname,
      rows: rows.slice(0, MAX_ROWS_PER_GROUP),
      best: rows[0].score,
      degraded: true,
    };
  }

  function searchDoc(plan, idx, docIdx) {
    var docname = idx.docnames[docIdx];
    return fetchPage(contentRoot() + docname + ".html").then(function (doc) {
      if (!doc) return fallbackDoc(plan, idx, docIdx);
      var box = doc.querySelector('[role="main"]');
      if (!box) return fallbackDoc(plan, idx, docIdx);
      var pageTitle = idx.titles[docIdx] || docname;
      var rows = [];
      collectSections(box).forEach(function (section, order) {
        // the page-title section exists only to hold the h1 (and any intro
        // text before the first subheading). When it carries no body text,
        // the group header already represents it — do not repeat it as a
        // contentless row (the furnace page used to show its title twice).
        if (section.heading === pageTitle && !section.body) return;
        var scored = scoreSection(plan, section);
        if (!scored) return;
        rows.push({
          title: section.heading || pageTitle,
          anchor: section.id ? "#" + section.id : "",
          chain: section.chain,
          snippet: bestSnippet(plan, section),
          score: scored.score,
          order: order,
        });
      });
      if (!rows.length) return null;
      rows.sort(function (a, b) {
        return b.score - a.score || a.order - b.order;
      });
      return {
        docIdx: docIdx,
        docname: docname,
        rows: rows.slice(0, MAX_ROWS_PER_GROUP),
        best: rows[0].score,
      };
    });
  }

  /* ---------------- result rendering (shared) ---------------- */

  function chipFor(title) {
    var chip = document.createElement("span");
    chip.className = "sd-res-book";
    chip.innerHTML =
      '<svg class="sd-icon" aria-hidden="true"><use href="#sd-i-book"></use></svg>';
    chip.appendChild(document.createTextNode(title));
    return chip;
  }

  function renderState(target, text) {
    target.innerHTML = "";
    var p = document.createElement("p");
    p.className = "sd-res-state";
    p.textContent = text;
    target.appendChild(p);
  }

  function renderBusy(target, query) {
    target.innerHTML = "";
    var p = document.createElement("p");
    p.className = "sd-res-count";
    p.textContent = "Searching for \u201C" + query + "\u201D\u2026";
    target.appendChild(p);
  }

  function renderResults(target, idx, plan, groups) {
    var books = readMap();
    target.innerHTML = "";
    var nav = [];
    var total = groups.reduce(function (sum, group) {
      return sum + group.rows.length;
    }, 0);
    var count = document.createElement("p");
    count.className = "sd-res-count";
    if (!groups.length) {
      count.textContent = "Nothing found for \u201C" + plan.raw + "\u201D";
      target.appendChild(count);
      var state = document.createElement("p");
      state.className = "sd-res-state";
      state.textContent = "Try fewer or different words.";
      target.appendChild(state);
      return nav;
    }
    count.textContent =
      groups.length +
      (groups.length === 1 ? " folio" : " folios") +
      " \u00B7 " +
      total +
      (total === 1 ? " section" : " sections") +
      " \u00B7 \u201C" +
      plan.raw +
      "\u201D";
    target.appendChild(count);

    groups.forEach(function (group) {
      var docname = idx.docnames[group.docIdx];
      var pageHref = contentRoot() + docname + ".html";
      var book = books[docname.split("/")[0]] || null;

      var box = document.createElement("div");
      box.className = "sd-res-group";
      var head = document.createElement("div");
      head.className = "sd-res-head";
      head.innerHTML =
        '<svg class="sd-icon" aria-hidden="true"><use href="#sd-i-file-text"></use></svg>';
      var headLink = document.createElement("a");
      headLink.setAttribute("href", pageHref);
      headLink.textContent = idx.titles[group.docIdx] || docname;
      head.appendChild(headLink);
      box.appendChild(head);
      nav.push({ row: head, link: headLink });

      group.rows.forEach(function (row) {
        var headTitle = idx.titles[group.docIdx] || docname;
        var item = document.createElement("div");
        item.className = "sd-res-item";
        var link = document.createElement("a");
        link.setAttribute("href", pageHref + row.anchor);
        if (row.chain.length > 1) {
          var trail = document.createElement("span");
          trail.className = "sd-res-trail";
          trail.textContent = row.chain.slice(1).join(" \u203A ");
          link.appendChild(trail);
        }
        // the top-level section is the page's own title: the group header
        // already carries it, so only subheadings repeat their heading
        if (row.title && row.title !== headTitle) {
          var what = document.createElement("span");
          what.className = "sd-res-what";
          what.textContent = row.title;
          link.appendChild(what);
        }
        if (row.snippet) {
          var snip = document.createElement("p");
          snip.className = "sd-res-snip";
          splitHighlight(row.snippet, plan).forEach(function (segment) {
            if (!segment.text) return;
            if (segment.hit) {
              var mark = document.createElement("mark");
              mark.className = "sd-res-mark";
              mark.textContent = segment.text;
              snip.appendChild(mark);
            } else {
              snip.appendChild(document.createTextNode(segment.text));
            }
          });
          link.appendChild(snip);
        }
        if (book && book.title) link.appendChild(chipFor(book.title));
        item.appendChild(link);
        box.appendChild(item);
        nav.push({ row: item, link: link });
      });
      target.appendChild(box);
    });
    return nav;
  }

  /** One searcher per surface (dialog / full page) with its own epoch so
      a fast typist's stale fetches never overwrite newer results. */
  function createSearcher(target, onRendered) {
    var epoch = 0;
    return function (query) {
      epoch += 1;
      var mine = epoch;
      var raw = String(query == null ? "" : query).trim();
      if (!raw) {
        renderState(target, "Type to search across the library.");
        if (onRendered) onRendered([]);
        return Promise.resolve(null);
      }
      renderBusy(target, raw);
      if (onRendered) onRendered([]);
      // the language pack must be present before the stemmer is used
      return loadIndex()
        .then(function (idx) {
          var plan = planQuery(raw);
          if (!plan.hasQuery) {
            renderState(target, "Type to search across the library.");
            if (onRendered) onRendered([]);
            return null;
          }
          var candidates = candidateDocs(plan, idx);
          if (!candidates.length) {
            if (mine === epoch) {
              renderResults(target, idx, plan, []);
              if (onRendered) onRendered([]);
            }
            return null;
          }
          // 0032 ③: render as candidate folios resolve (progressive),
          // then do one final ordered pass. With cached fetches this is
          // usually one visible frame; on a slow disk it puts the first
          // hits on screen instead of a spinner.
          var arrived = [];
          var scheduled = false;
          var finished = false;
          function ordered() {
            return arrived
              .slice()
              .sort(function (a, b) {
                return b.best - a.best || a.docIdx - b.docIdx;
              })
              .slice(0, MAX_GROUPS);
          }
          function flush() {
            scheduled = false;
            if (mine !== epoch || finished) return;
            renderResults(target, idx, plan, ordered());
          }
          function schedule() {
            if (scheduled) return;
            scheduled = true;
            window.setTimeout(flush, 0);
          }
          return Promise.all(
            candidates.map(function (hit) {
              return searchDoc(plan, idx, hit.doc).then(function (doc) {
                if (mine !== epoch) return null;
                if (doc && doc.rows.length) {
                  arrived.push(doc);
                  schedule();
                }
                return doc;
              });
            })
          ).then(function () {
            if (mine !== epoch) return null;
            finished = true;
            var groups = ordered();
            var nav = renderResults(target, idx, plan, groups);
            if (onRendered) onRendered(nav);
            return { plan: plan, groups: groups };
          });
        })
        .catch(function () {
          if (mine !== epoch) return null;
          renderState(target, "Search is not available in this preview context.");
          if (onRendered) onRendered([]);
          return null;
        });
    };
  }

  /* ================================================================ */
  /* 4. Search dialog (0031 ①, centred + x close by 0032 ②④)          */
  /* ================================================================ */

  var ui = null;
  var dialogSearch = null;
  var navList = [];
  var navIndex = -1;
  var debounce = null;
  var lastQuery = "";

  function navReset(items) {
    navList = items || [];
    navIndex = -1;
    navList.forEach(function (item) {
      item.row.classList.remove("sd-res-active");
    });
  }

  function navMove(step) {
    if (!navList.length) return;
    var next = navIndex + step;
    if (next < 0) next = navList.length - 1;
    if (next >= navList.length) next = 0;
    if (navIndex !== -1 && navList[navIndex]) {
      navList[navIndex].row.classList.remove("sd-res-active");
    }
    navIndex = next;
    navList[navIndex].row.classList.add("sd-res-active");
    navList[navIndex].row.scrollIntoView({ block: "nearest" });
  }

  function navPick() {
    if (navIndex !== -1 && navList[navIndex]) {
      navList[navIndex].link.click();
      return;
    }
    var first = ui.body.querySelector(".sd-res-head a, .sd-res-item a");
    if (first) first.click();
  }

  function syncFullLink(query) {
    if (!ui) return;
    var href = contentRoot() + "search.html";
    if (query && query.trim()) {
      href += "?q=" + encodeURIComponent(query.trim());
    }
    ui.full.setAttribute("href", href);
  }

  function execute(query) {
    lastQuery = query;
    syncFullLink(query);
    if (dialogSearch) dialogSearch(query);
  }

  function openDialog(prefill) {
    if (!ui) {
      ui = buildDialog();
      wireDialog();
      dialogSearch = createSearcher(ui.body, function (nav) {
        navReset(nav);
      });
    }
    ui.trigger = document.activeElement;
    ui.backdrop.hidden = false;
    ui.panel.hidden = false;
    document.body.classList.add("sd-dlg-lock");
    lastQuery = "";
    ui.input.value = prefill || "";
    if (prefill && prefill.trim()) execute(prefill);
    else renderState(ui.body, "Type to search across the library.");
    syncFullLink(prefill || "");
    window.setTimeout(function () {
      ui.input.focus();
      ui.input.setSelectionRange(ui.input.value.length, ui.input.value.length);
    }, 0);
  }

  function closeDialog() {
    if (!ui) return;
    ui.backdrop.hidden = true;
    ui.panel.hidden = true;
    document.body.classList.remove("sd-dlg-lock");
    if (ui.trigger && ui.trigger.focus) ui.trigger.focus();
  }

  function buildDialog() {
    var backdrop = document.createElement("div");
    backdrop.className = "sd-dlg-backdrop";
    backdrop.hidden = true;

    var panel = document.createElement("div");
    panel.className = "sd-dlg";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "Search the library");
    panel.hidden = true;
    panel.innerHTML =
      '<div class="sd-dlg-row">' +
      '<svg class="sd-icon" aria-hidden="true"><use href="#sd-i-search"></use></svg>' +
      '<input type="text" class="sd-dlg-input" placeholder="Search the library" aria-label="Search the library" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />' +
      '<button type="button" class="sd-dlg-close" aria-label="Close search" title="Close search">' +
      '<svg class="sd-icon" aria-hidden="true"><use href="#sd-i-x"></use></svg>' +
      "</button>" +
      "</div>" +
      '<div class="sd-dlg-body" tabindex="-1"></div>' +
      '<div class="sd-dlg-foot">' +
      '<span><kbd>&#8593;&#8595;</kbd> navigate &nbsp;\u00B7&nbsp; <kbd>Enter</kbd> select &nbsp;\u00B7&nbsp; <kbd>esc</kbd> close</span>' +
      '<a class="sd-dlg-full" href="' + contentRoot() + 'search.html">Full results page</a>' +
      "</div>";
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);
    return {
      backdrop: backdrop,
      panel: panel,
      input: panel.querySelector(".sd-dlg-input"),
      close: panel.querySelector(".sd-dlg-close"),
      body: panel.querySelector(".sd-dlg-body"),
      full: panel.querySelector(".sd-dlg-full"),
    };
  }

  function wireDialog() {
    ui.backdrop.addEventListener("click", closeDialog);
    ui.close.addEventListener("click", closeDialog);
    ui.input.addEventListener("input", function () {
      var value = ui.input.value;
      if (value.trim() === lastQuery.trim()) return;
      if (debounce) window.clearTimeout(debounce);
      if (!value.trim()) {
        debounce = null;
        lastQuery = "";
        renderState(ui.body, "Type to search across the library.");
        navReset([]);
        syncFullLink("");
        return;
      }
      debounce = window.setTimeout(function () {
        debounce = null;
        execute(value);
      }, 160);
    });
    ui.input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        navMove(1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        navMove(-1);
      } else if (event.key === "Enter") {
        event.preventDefault();
        navPick();
      }
    });

    ui.panel.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDialog();
      } else if (event.key === "Tab") {
        event.preventDefault();
        var order = [ui.input, ui.close, ui.full];
        var at = order.indexOf(document.activeElement);
        var step = event.shiftKey ? -1 : 1;
        var next = (at + step + order.length) % order.length;
        order[next].focus();
      }
    });
  }

  function wireSearchField() {
    var form = document.querySelector(".sd-search");
    if (!form) return;
    var input = form.querySelector("input[name='q']");
    var clear = form.querySelector(".sd-search-clear");

    function syncClear() {
      form.classList.toggle("sd-has-value", !!(input && input.value));
    }

    if (input) {
      input.addEventListener("input", syncClear);
      input.addEventListener("click", function () {
        openDialog(input.value);
      });
    }
    if (clear) {
      clear.addEventListener("click", function (event) {
        // 0032 ④: clear ONLY — never the dialog trigger
        event.preventDefault();
        event.stopPropagation();
        if (input) {
          input.value = "";
          input.focus();
        }
        syncClear();
      });
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      openDialog(input ? input.value : "");
    });
    syncClear();
  }

  function wireShortcuts() {
    document.addEventListener("keydown", function (event) {
      var open = ui && !ui.panel.hidden;
      if (
        (event.ctrlKey || event.metaKey) &&
        (event.key === "k" || event.key === "K")
      ) {
        event.preventDefault();
        if (open) closeDialog();
        else openDialog("");
      } else if (event.key === "Escape" && open) {
        closeDialog();
      }
    });
  }

  /* ================================================================ */
  /* 5. Full search page (0032 ②)                                     */
  /* ================================================================ */

  function wirePageSearch() {
    var form = document.querySelector(".sd-searchpage-form");
    var target = document.getElementById("search-results");
    if (!form || !target) return;
    var input = form.querySelector("input[name='q']");
    var searcher = createSearcher(target, null);

    function render(query, keepUrl) {
      if (input) input.value = query;
      if (keepUrl && window.history && window.history.replaceState) {
        try {
          var suffix = query.trim()
            ? "?q=" + encodeURIComponent(query.trim())
            : window.location.pathname;
          window.history.replaceState(null, "", suffix);
        } catch (err) {
          // file:// origins may refuse replaceState; the search still runs
        }
      }
      if (!query.trim()) {
        renderState(target, "Type a word or a sentence to search the library.");
        return;
      }
      searcher(query);
    }

    var initial = "";
    try {
      initial = new URLSearchParams(window.location.search).get("q") || "";
    } catch (err) {
      initial = "";
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      render(input ? input.value : "", true);
    });
    render(initial, false);
    window.addEventListener("popstate", function () {
      var query = "";
      try {
        query = new URLSearchParams(window.location.search).get("q") || "";
      } catch (err) {
        query = "";
      }
      render(query, false);
    });
  }

  /* ================================================================ */
  /* 6. On-This-Page scrollspy (0031 7.v, title fix 0032 ⑨)           */
  /* ================================================================ */

  function wireScrollspy() {
    var rail = document.querySelector(".sd-toc");
    var article = document.querySelector(".sd-article");
    if (!rail || !article) return;

    var entries = [];
    rail.querySelectorAll("a[href^='#']").forEach(function (link) {
      var href = link.getAttribute("href") || "#";
      var id = href.slice(1);
      var target = null;
      if (!id) {
        // 0032 ⑨: the page-title rail entry is `href="#"` — map it to
        // the article's own title instead of dropping it from the spy.
        target = article.querySelector("h1") || article;
      } else {
        try {
          target = document.getElementById(decodeURIComponent(id));
        } catch (err) {
          target = document.getElementById(id);
        }
      }
      if (target) entries.push({ link: link, target: target });
    });
    if (!entries.length) return;

    var active = null;
    function setActive(link) {
      if (active === link) return;
      if (active) active.classList.remove("sd-toc-active");
      active = link || null;
      if (active) active.classList.add("sd-toc-active");
    }

    // Direct measurement on scroll: scroll events are already coalesced
    // per frame, the rail holds a handful of headings, and this keeps the
    // spy correct in environments that throttle rAF (0032 ⑨).
    function spy() {
      var line = window.scrollY + 140; // just below the top bar
      var best = null;
      entries.forEach(function (entry) {
        var top = entry.target.getBoundingClientRect().top + window.scrollY;
        if (top <= line) best = entry;
      });
      // a short final section may never cross the line; at the bottom of
      // the page the last heading is what the reader is looking at
      var atBottom =
        window.innerHeight + window.scrollY >=
        document.documentElement.scrollHeight - 2;
      if (atBottom) best = entries[entries.length - 1];
      setActive(best ? best.link : entries[0].link);
    }

    window.addEventListener("scroll", spy, { passive: true });
    window.addEventListener("resize", spy);
    entries.forEach(function (entry) {
      entry.link.addEventListener("click", function () {
        setActive(entry.link); // direct anchor click highlights at once
      });
    });
    spy();
  }

  /* ================================================================ */
  /* 7. Panel collapse (0031 7.viii, placement 0032 ⑧)                */
  /* ================================================================ */

  function wirePanelToggle() {
    var toggles = document.querySelectorAll(".sd-panel-toggle");
    var shell = document.querySelector(".sd-shell");
    if (!toggles.length || !shell) return;
    var expand = shell.querySelector(".sd-panel-expand");
    var collapse = document.querySelector(".sd-panel-collapse");
    var KEY = "sd-panel-open";
    var stored = null;
    try {
      stored = window.localStorage.getItem(KEY);
    } catch (err) {
      stored = null; // private mode: ephemeral state is fine
    }
    var open = stored !== "closed";

    function apply() {
      shell.classList.toggle("sd-panel-off", !open);
      // 0034 follow-up: the head script's pre-paint marker has done its
      // job; from here the shell class is the single source of truth.
      document.documentElement.classList.remove("sd-panel-pending-off");
      toggles.forEach(function (button) {
        button.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    apply();
    toggles.forEach(function (button) {
      button.addEventListener("click", function () {
        open = !open;
        try {
          window.localStorage.setItem(KEY, open ? "open" : "closed");
        } catch (err) {
          // state not persisted — acceptable (micro-default, disclosed)
        }
        apply();
        // keep keyboard focus on the control that just became visible
        var next = open ? collapse : expand;
        if (next) next.focus();
      });
    });
  }

  /* ================================================================ */
  /* Boot — the theme script is the LAST body script, so the DOM      */
  /* (sidebar, article, page results) is already in place.            */
  /* ================================================================ */

  document
    .querySelectorAll(".sd-article .highlight, .admonition .highlight")
    .forEach(wireCodeBlock);
  wireScrollspy();
  wireSearchField();
  wirePageSearch();
  wirePanelToggle();
  wireShortcuts();

  /* Test seam: the DOM-free core is exercised by the backend Node test
     (tests/test_theme_search_js.py) — no production code reads this. */
  window.__sdSearch = {
    planQuery: planQuery,
    scoreSection: scoreSection,
    splitHighlight: splitHighlight,
    bestSnippet: bestSnippet,
    splitWords: splitWords,
    phrasePattern: phrasePattern,
    languageFromClass: languageFromClass,
  };
})();
