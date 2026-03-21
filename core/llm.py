"""
Interface com o Groq.
Centraliza todas as chamadas LLM — se um dia mudar de provider,
só mexe aqui.
"""

from groq import Groq
from core.logger import get_logger

log = get_logger(__name__)


class LLMClient:
    def __init__(self, cfg: dict):
        llm_cfg = cfg["llm"]
        self.client = Groq(api_key=llm_cfg["api_key"])
        self.model = llm_cfg["model"]
        self.temperature = llm_cfg["temperature"]
        self.max_tokens = llm_cfg["max_tokens"]

    def chat(self, system: str, user: str) -> str:
        """
        Envia uma mensagem e retorna a resposta como string.
        system = instrução de comportamento
        user   = o pedido em si
        """
        log.debug(f"LLM call → model={self.model} | user={user[:80]}...")
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        result = response.choices[0].message.content
        log.debug(f"LLM resposta → {result[:80]}...")
        return result

    def chat_with_history(self, system: str, history: list[dict]) -> str:
        """
        Versão com histórico de conversa completo.
        history = lista de {"role": "user"/"assistant", "content": "..."}
        """
        messages = [{"role": "system", "content": system}] + history
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content
