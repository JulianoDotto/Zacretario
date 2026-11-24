import logging

import anthropic

from zacretario.agent.prompt import build_system_prompt
from zacretario.agent.registry import Tool, ToolContext, ToolError, to_api_params

logger = logging.getLogger(__name__)

REFUSAL_MESSAGE = (
    "Desculpe, não posso ajudar com isso. Posso cuidar da sua agenda e das suas tarefas 🙂"
)
_UNEXPECTED_ERROR = "Erro inesperado ao executar a ferramenta. Tente de novo ou avise o usuário."


class AgentError(Exception):
    pass


class Agent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str,
        tools: list[Tool],
        max_iterations: int = 8,
    ) -> None:
        self.client = client
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations

    def reply(
        self,
        ctx: ToolContext,
        user_name: str,
        history: list[tuple[str, str]],
        text: str,
    ) -> str:
        system = build_system_prompt(user_name, ctx.now.astimezone(ctx.tz))
        tools = to_api_params(list(self.tools.values()))
        messages = _build_messages(history, text)

        for _ in range(self.max_iterations):
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                tools=tools,
                messages=messages,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if response.stop_reason == "end_turn":
                return _join_text(response.content)
            if response.stop_reason == "refusal":
                return REFUSAL_MESSAGE
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                results = [
                    self._run_tool(ctx, block)
                    for block in response.content
                    if block.type == "tool_use"
                ]
                messages.append({"role": "user", "content": results})
                continue
            raise AgentError(f"Resposta interrompida (stop_reason={response.stop_reason})")

        raise AgentError(f"Limite de {self.max_iterations} iterações atingido")

    def _run_tool(self, ctx: ToolContext, block) -> dict:
        result = {"type": "tool_result", "tool_use_id": block.id}
        tool = self.tools.get(block.name)
        if tool is None:
            return {**result, "content": f"Ferramenta desconhecida: {block.name}", "is_error": True}
        try:
            return {**result, "content": tool.handler(ctx, block.input)}
        except ToolError as error:
            return {**result, "content": str(error), "is_error": True}
        except Exception:
            # The traceback goes to our logs only; the model just learns that it failed.
            logger.exception("Tool %s failed", block.name)
            return {**result, "content": _UNEXPECTED_ERROR, "is_error": True}


def _build_messages(history: list[tuple[str, str]], text: str) -> list[dict]:
    # The API requires roles to alternate starting with "user": drop leading assistant
    # turns and merge consecutive turns of the same role.
    messages: list[dict] = []
    for role, content in [*history, ("user", text)]:
        if not messages and role != "user":
            continue
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + content
        else:
            messages.append({"role": role, "content": content})
    return messages


def _join_text(content) -> str:
    return "".join(block.text for block in content if block.type == "text").strip()
