from zacretario.agent.registry import Tool, ToolContext, ToolError, register
from zacretario.repositories import todos


def _add_todo(ctx: ToolContext, args: dict) -> str:
    todo = todos.add_todo(ctx.session, ctx.owner, args["text"])
    return f"TODO #{todo.id} criado: {todo.text}"


def _list_todos(ctx: ToolContext, args: dict) -> str:
    open_todos = todos.list_open_todos(ctx.session, ctx.owner)
    if not open_todos:
        return "Nenhum TODO em aberto."
    return "\n".join(f"#{todo.id} {todo.text}" for todo in open_todos)


def _complete_todo(ctx: ToolContext, args: dict) -> str:
    todo = todos.complete_todo(ctx.session, ctx.owner, args["todo_id"])
    if todo is None:
        raise ToolError(f"TODO #{args['todo_id']} não encontrado")
    return f"TODO #{todo.id} concluído: {todo.text}"


def _delete_todo(ctx: ToolContext, args: dict) -> str:
    if not todos.delete_todo(ctx.session, ctx.owner, args["todo_id"]):
        raise ToolError(f"TODO #{args['todo_id']} não encontrado")
    return f"TODO #{args['todo_id']} apagado"


_NO_INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}
_TODO_ID_SCHEMA = {
    "type": "object",
    "properties": {"todo_id": {"type": "integer", "description": "Número do TODO."}},
    "required": ["todo_id"],
    "additionalProperties": False,
}

register(
    Tool(
        name="add_todo",
        description="Cria um TODO (tarefa sem horário) para o usuário.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Texto do TODO."}},
            "required": ["text"],
            "additionalProperties": False,
        },
        handler=_add_todo,
    )
)
register(
    Tool(
        name="list_todos",
        description="Lista os TODOs em aberto do usuário.",
        input_schema=_NO_INPUT_SCHEMA,
        handler=_list_todos,
    )
)
register(
    Tool(
        name="complete_todo",
        description="Marca um TODO como concluído.",
        input_schema=_TODO_ID_SCHEMA,
        handler=_complete_todo,
    )
)
register(
    Tool(
        name="delete_todo",
        description="Apaga um TODO.",
        input_schema=_TODO_ID_SCHEMA,
        handler=_delete_todo,
    )
)
