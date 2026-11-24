# Future improvements

Ideas left out of v1. Each one lists the extension point that absorbs it, so none should need a rewrite.

## Shared household items (e.g. a shared shopping list)

Extension point: the `owner` column.

Todos and preferences already carry an `owner` (`src/zacretario/models.py`). A shared owner such as `casa` can be added next to the two user numbers. The work is in the todo tools (`src/zacretario/agent/todo_tools.py`) and the prompt, so the agent can tell "my list" from "the house list", plus a rule for who may read and write shared rows. Personal data must stay isolated.

## Audio, images and forwarded messages

Extension point: the channel adapter and `IncomingMessage.type`.

`src/zacretario/channels/whatsapp.py` parses the Meta payload into an `IncomingMessage`, and `src/zacretario/service.py` is the single place that branches on `message.type` (anything other than text currently gets a "text only" notice). Audio would add a branch there that downloads the media and transcribes it, then hands the resulting text to the unchanged agent. Images and forwarded messages follow the same pattern.

## Proactive reminders

Extension points: the tool registry and the channel adapter.

Sending outside a user message needs a scheduled job that calls the adapter's send function (`src/zacretario/channels/whatsapp.py`). Reminders to create or edit would be new skills registered in `src/zacretario/agent/registry.py` and imported in `src/zacretario/agent/__init__.py`, with a table for pending reminders. Outside the 24-hour customer-service window, WhatsApp requires approved message templates.

## Other calendars (Outlook, iCloud)

Extension point: `CalendarProvider`.

`src/zacretario/calendar/base.py` defines the interface and `src/zacretario/calendar/google.py` is the first implementation. A new provider implements the same interface and is selected per user. The calendar tools and the agent do not change.

## Other channels (Telegram)

Extension point: the channel adapter.

The agent takes text and returns text, and knows nothing about WhatsApp. A Telegram adapter under `src/zacretario/channels/` would parse its updates into the same `IncomingMessage` and send replies, with its own webhook route in `src/zacretario/main.py`. The allowlist would need to cover Telegram user IDs.

## New skills in general

Extension point: the tool registry.

Each skill is a schema plus a function registered in `src/zacretario/agent/registry.py`. Add a module under `src/zacretario/agent/` and import it in `src/zacretario/agent/__init__.py`; the agent loop is untouched.
