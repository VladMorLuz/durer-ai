"""
Dürer AI — Relatório pós-desenho.
Depois de cada tentativa avaliada, a IA reflete sobre o que aprendeu
e o que vai tentar diferente. Salvo em reports/ como diário de prática.
"""

import json
from pathlib import Path
from datetime import datetime
from core.llm import LLMClient
from core.logger import get_logger

log = get_logger(__name__)

SYSTEM_REFLEXAO = """Você é o Dürer AI refletindo sobre uma tentativa de desenho.
Você tentou desenhar algo, um crítico avaliou o resultado, e agora você precisa
escrever uma reflexão honesta sobre o que aconteceu.

Escreva em primeira pessoa, como um artista em seu diário de prática.
Inclua:
1. O que você tentou fazer e como planejou
2. O que o crítico disse sobre o resultado
3. O que você acha que deu certo e o que não funcionou
4. O que você vai tentar diferente na próxima vez
5. Que conceitos você precisa estudar mais para melhorar

Seja genuíno e específico. Este é seu processo de aprendizado."""


class PostReportGenerator:
    def __init__(self, cfg: dict):
        self.llm = LLMClient(cfg)
        self.reports_dir = Path(cfg["paths"]["reports"])

    def gerar(self, pedido: str, plano: list, feedback: dict) -> Path:
        """
        Gera reflexão pós-desenho e salva em reports/.
        """
        log.info("Gerando relatório pós-desenho...")

        contexto = (
            f"Pedido: {pedido}\n\n"
            f"Meu plano de execução:\n{json.dumps(plano, ensure_ascii=False, indent=2)}\n\n"
            f"Feedback do crítico:\n"
            f"- Nota geral: {feedback.get('nota_geral', '?')}/10\n"
            f"- O que funcionou: {feedback.get('o_que_funcionou', '')}\n"
            f"- Problemas: {', '.join(feedback.get('problemas', []))}\n"
            f"- Sugestões: {', '.join(feedback.get('sugestoes', []))}\n"
            f"- Para próxima tentativa: {feedback.get('proxima_tentativa', '')}\n"
            f"- Conceitos para estudar: {', '.join(feedback.get('conceitos_para_estudar', []))}"
        )

        reflexao = self.llm.chat(system=SYSTEM_REFLEXAO, user=contexto)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = pedido[:40].replace(" ", "_").lower()
        caminho = self.reports_dir / f"{timestamp}_pratica_{slug}.md"

        cabecalho = (
            f"# Diário de Prática — Dürer AI\n"
            f"**Pedido:** {pedido}\n"
            f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"**Nota do crítico:** {feedback.get('nota_geral', '?')}/10\n\n"
            f"---\n\n"
        )

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(cabecalho + reflexao)

        log.info(f"Relatório de prática salvo: {caminho.name}")
        return caminho