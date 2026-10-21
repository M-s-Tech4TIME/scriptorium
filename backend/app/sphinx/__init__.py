"""Sphinx site staging + build support (M4, decision 0026).

`sourcegen` plans the deterministic Sphinx source tree for one
Athenaeum = one site build; the runner (M4-C3) materializes it into the
per-build workspace and invokes Sphinx inside the ruled sandbox.
"""
