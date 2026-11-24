from sqlalchemy.orm import Session

from zacretario.models import GoogleCredential


def get_refresh_token(session: Session, owner: str) -> str | None:
    row = session.get(GoogleCredential, owner)
    return row.refresh_token if row is not None else None


def save_refresh_token(session: Session, owner: str, token: str) -> None:
    row = session.get(GoogleCredential, owner)
    if row is None:
        session.add(GoogleCredential(owner=owner, refresh_token=token))
    else:
        row.refresh_token = token
    session.commit()
