"""Authorize one user's Google Calendar and store the refresh token.

Usage: python -m uv run python scripts/authorize_google.py <owner>
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from zacretario.calendar.google import SCOPES
from zacretario.config import get_settings
from zacretario.db import make_session_factory, session_scope
from zacretario.repositories.credentials import save_refresh_token


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: authorize_google.py <owner>")
        return 1
    owner = sys.argv[1]
    settings = get_settings()
    valid = sorted(settings.allowed_users.values())
    if owner not in valid:
        print(f"Unknown owner '{owner}'. Valid owners: {', '.join(valid)}")
        return 1

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        print("Google did not return a refresh token. Try again.")
        return 1
    with session_scope(make_session_factory(settings.database_url)) as session:
        save_refresh_token(session, owner, creds.refresh_token)
    print(f"Saved Google refresh token for '{owner}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
