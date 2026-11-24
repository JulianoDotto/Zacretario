from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from zacretario.models import Todo


def add_todo(session: Session, owner: str, text: str) -> Todo:
    todo = Todo(owner=owner, text=text)
    session.add(todo)
    session.commit()
    return todo


def list_open_todos(session: Session, owner: str) -> list[Todo]:
    query = select(Todo).where(Todo.owner == owner, Todo.done.is_(False)).order_by(Todo.id)
    return list(session.scalars(query))


def _get_owned(session: Session, owner: str, todo_id: int) -> Todo | None:
    # Another owner's todo is treated exactly like a missing one.
    todo = session.get(Todo, todo_id)
    return todo if todo is not None and todo.owner == owner else None


def complete_todo(session: Session, owner: str, todo_id: int) -> Todo | None:
    todo = _get_owned(session, owner, todo_id)
    if todo is None:
        return None
    todo.done = True
    todo.done_at = datetime.now(UTC)
    session.commit()
    return todo


def delete_todo(session: Session, owner: str, todo_id: int) -> bool:
    todo = _get_owned(session, owner, todo_id)
    if todo is None:
        return False
    session.delete(todo)
    session.commit()
    return True
