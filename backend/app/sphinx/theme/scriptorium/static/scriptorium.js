/* Scriptorium theme support script — M4-C3.5 (decision 0028 ③B).
   The ONE first-party script the artifact carries (0027 JS clause as
   amended by 0028): code-copy buttons for every .highlight block.
   ~40 lines on purpose; no dependencies, no network.

   Copy icon: Tabler "copy" path, v3.36.0, MIT (see layout.html
   attribution) — used via markup here because the button is created
   after the sprite is available anyway (the sprite lives on every
   page; the button uses <use> to stay single-sourced). */

"use strict";

(function () {
  var BUTTON_TAG =
    '<button type="button" class="sd-copy" aria-label="Copy code" title="Copy code">' +
    '<svg class="sd-icon" aria-hidden="true"><use href="#sd-i-copy"></use></svg>' +
    "</button>";

  function wire(block) {
    if (block.querySelector(".sd-copy")) return; // idempotent
    var button = document.createElement("span");
    button.outerHTML = BUTTON_TAG;
    button = block.querySelector(".sd-copy");
    button.addEventListener("click", function () {
      var text = block.querySelector("pre") ? block.querySelector("pre").textContent : "";
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        fallbackCopy(text);
      } else {
        navigator.clipboard.writeText(text).catch(function () {
          fallbackCopy(text);
        });
      }
      button.classList.add("sd-copied");
      window.setTimeout(function () {
        button.classList.remove("sd-copied");
      }, 1600);
    });
  }

  function fallbackCopy(text) {
    // non-secure-context path; file:// is secure, memset fallback kept tiny
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

  document.querySelectorAll(".sd-article .highlight, .admonition .highlight").forEach(wire);
})();
