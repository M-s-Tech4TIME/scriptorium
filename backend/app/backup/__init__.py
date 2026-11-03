"""Backup/restore package (decision 0039).

Editorial and Full archives share one manifest/integrity model; ZIP and
``.tar.gz`` are thin container adapters. Archives are untrusted input and
are fully validated before any database write.
"""
