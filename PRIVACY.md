# Privacy Policy — Zacretário

Zacretário is a personal, non-commercial assistant used only by its author and a small set of people he authorizes. It is not offered to the public.

## What data it accesses

- **WhatsApp messages** sent by authorized phone numbers to the Zacretário number, to understand requests.
- **Google Calendar events** of the authorized user's primary calendar (scope `calendar.events`), to list, create, update and delete events at the user's request.
- **To-do items, preferences and a short conversation history** (last messages, up to 24 hours) stored in the project's own database.

## How data is used

Data is used only to provide the assistant's features to the same user who sent the request. Message text is sent to Anthropic's Claude API to interpret the request. Nothing is sold, shared for advertising, or used to train models by this project.

## Storage and retention

Data is stored in a private Postgres database controlled by the author. Messages from unauthorized numbers are ignored and not stored. Users can ask the author to delete their data at any time, and can revoke Google access at https://myaccount.google.com/permissions.

## Contact

Open an issue at https://github.com/JulianoDotto/Zacretario/issues.
