# Learning log

One short entry per stage of moving Zacretário from Python to n8n: what was done, the n8n concept behind it, and what went wrong. The plan is in [`superpowers/plans/2026-11-25-n8n-migration.md`](superpowers/plans/2026-11-25-n8n-migration.md).

## Task 0 — Why n8n (2026-11-25)

Zacretário started as a Python/FastAPI app with a hand-written Claude agent. Learning Python through it was a convenience, not the goal: n8n fits where I want to go next, which is freelance automation work. The project's priorities are now (1) learning n8n, (2) a portfolio piece, and (3) later, a plug-and-play base I can adapt for each client.

The Python version is kept under the git tag `v1-python`. WhatsApp moves from Meta's Cloud API to Evolution API; see the [design](superpowers/specs/2026-11-25-n8n-migration-design.md) for why.

How we work: Claude navigates to the right page and explains each step; I perform every action myself.
