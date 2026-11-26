# Why n8n and Evolution API

Zacretário v1 was a Python/FastAPI app talking to WhatsApp through Meta's official Cloud API. The current version runs as n8n workflows on a single VPS and reaches WhatsApp through Evolution API. This page records why both changes were made and what was given up. The Python version is kept under the git tag `v1-python`.

## From Python to n8n

Learning Python was a convenience of v1, not the goal. The goal moved to freelance automation work, where n8n is the tool clients ask for. The project's priorities became, in order:

1. **Learning n8n**, by rebuilding a real product in it rather than following tutorials.
2. **A portfolio piece** showing the same product in two stacks, with the decisions written down.
3. **A plug-and-play base** for future clients: everything that changes per person lives in the `users` table and in n8n credentials, never inside the nodes.

What carried over unchanged: the behaviour (the same system prompt, the same tools, the same confirmation and safety rules) and the hard parts of the logic, ported into JavaScript Code nodes (date handling, free-slot search, the "events with guests are read-only" rule). What was given up: the Python test suite (the Code nodes are tested outside n8n with Node.js instead), static typing, and code review as plain diffs — workflows are exported as JSON, which reviews less well than code.

## From Meta's Cloud API to Evolution API

The first real setup of the Cloud API ([meta-whatsapp-notes.md](meta-whatsapp-notes.md)) went through app publishing, the WABA subscription, a test number that does not deliver to Brazil (error 130497), and a Meta-provided number blocked until the display name is approved (error 131037), which in practice requires business verification with a CNPJ. Tokens expired and the callback URL changed with every tunnel. For a two-person assistant that cost did not pay off.

| | Option | For | Against |
|---|---|---|---|
| **Chosen** | **Evolution API** (self-hosted, Docker) | The tool the Brazilian n8n market uses; good n8n material in Portuguese; one "instance" per number fits one client per instance; QR-code pairing | Unofficial (ban risk); heavier (needs Postgres); Apache 2.0 with extra conditions |
| | WuzAPI | MIT with no conditions; light | Little n8n usage; teaches less of the market |
| | Meta Cloud API | Official | The bureaucracy above |

Software cost is zero for both unofficial options; the real costs are the VPS, Claude API tokens and a dedicated SIM.

## Risks accepted

- **The number can be banned.** Evolution API connects as a linked device (like WhatsApp Web), which is outside WhatsApp's Terms. Mitigation: a dedicated number, never a personal one; the bot only answers people who write to it; no bulk messages.
- **Protocol changes can break the connection** until Evolution API updates. Mitigation: a pinned image version and a documented update step.
- **Licence changes.** Evolution API's 2.4 pre-release registers with a licensing server. Mitigation: the image stays pinned to 2.3.x; re-check before upgrading.
- **One small VPS** (1 vCPU, 4 GB) runs n8n, Postgres and Evolution API; so far with room to spare.

If the number is banned: pair another dedicated SIM in the Evolution manager (see [setup.md](setup.md#whatsapp-evolution-api)). Going back to the official API is possible from the `v1-python` tag.

## Licence notice

Zacretário uses [Evolution API](https://github.com/EvolutionAPI/evolution-api) (Apache 2.0 with additional conditions). Its manager keeps the Evolution logo and copyright, and this notice states that the system uses Evolution API.
