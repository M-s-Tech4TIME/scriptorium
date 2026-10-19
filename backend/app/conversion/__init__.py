"""TipTap↔RST/MyST converters (decision 0017, Q-M2-1=A).

Node scope = exactly the TipTap starter-kit 3.31.4 set:
doc, paragraph, heading(1-6), bulletList/orderedList/listItem, codeBlock,
blockquote, hardBreak, horizontalRule, and text marks
bold/italic/strike/code/link/underline.

Both RST (docutils parser) and MyST (`myst_parser.parsers.docutils_.Parser`)
parse into docutils doctrees — one walker imports both. Unmapped *content*
nodes raise ConversionError (fail-loud, no silent data loss); aura nodes
(system_message, comment, target, pending, substitution_definition) are
ignored by design.
"""

from __future__ import annotations

from .export_myst import export_myst
from .export_rst import export_rst
from .import_doc import ConversionError, import_document

__all__ = ["ConversionError", "export_myst", "export_rst", "import_document"]
