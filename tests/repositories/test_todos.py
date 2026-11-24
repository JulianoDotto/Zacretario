from zacretario.repositories.todos import add_todo, complete_todo, delete_todo, list_open_todos


def test_add_and_list_open_todos(session):
    add_todo(session, "juliano", "Comprar ração dos gatos")
    add_todo(session, "juliano", "Trocar lâmpada")

    texts = [todo.text for todo in list_open_todos(session, "juliano")]

    assert texts == ["Comprar ração dos gatos", "Trocar lâmpada"]


def test_complete_todo_removes_from_open_list(session):
    todo = add_todo(session, "juliano", "Trocar lâmpada")

    completed = complete_todo(session, "juliano", todo.id)

    assert completed is not None
    assert completed.done is True
    assert completed.done_at is not None
    assert list_open_todos(session, "juliano") == []


def test_delete_todo(session):
    todo = add_todo(session, "juliano", "Trocar lâmpada")

    assert delete_todo(session, "juliano", todo.id) is True
    assert list_open_todos(session, "juliano") == []
    assert delete_todo(session, "juliano", todo.id) is False


def test_owners_are_isolated(session):
    todo = add_todo(session, "bruna", "Pagar boleto")

    assert list_open_todos(session, "juliano") == []
    assert complete_todo(session, "juliano", todo.id) is None
    assert delete_todo(session, "juliano", todo.id) is False
    assert [t.text for t in list_open_todos(session, "bruna")] == ["Pagar boleto"]
