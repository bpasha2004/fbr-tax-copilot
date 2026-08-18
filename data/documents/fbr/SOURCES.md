# Authoritative FBR sources

- Finance Act 2026: https://download1.fbr.gov.pk/Docs/20266291261044366FinanceAct2026.pdf
- Income Tax Ordinance 2001 (amended 20.02.2026): repository copy is used only for non-2026-27 rules unless a newer official source is fetched.

Current-year retrieval fails closed if Finance Act 2026 is not indexed.
For production, pin the SHA-256 digest in `config/.env.prod` as `FBR_FINANCE_ACT_2026_SHA256` after obtaining the official PDF through the approved source-management process.
