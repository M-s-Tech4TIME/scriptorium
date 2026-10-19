# Changelog

## 2026-10-19 — M2 part 1: refresh-token store (decision 0017)

- `refresh_tokens` table (migration `0002`): family/jti/parent chain, expiry +
  revocation state (`rotated|reuse|logout|expired`); token material never stored.
- `auth.py`: `create_token_pair` now mints refresh tokens with `jti`+`fam` claims
  (returns 4-tuple); `decode_refresh` requires store claims;
  `rotate_refresh` implements family-based reuse detection — reused/unknown
  tokens burn their whole chain (401 force re-login); `revoke_family` reused
  by future logout route.
- Tests: offline claim strictness (4) + live rotation/reuse/burn scenarios on
  PG18 in CI (`test_rotation_then_reuse_burns_family`,
  `test_unknown_jti_is_reuse`); migration round-trip covers 9 tables.
- Approved by owner 2026-10-19 (Q-M2-2=A); see `docs/decisions/0017-m2-design.md`.
