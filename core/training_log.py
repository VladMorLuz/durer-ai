"""
Registro de cada tentativa de desenho.
Alimenta o training_log.jsonl com o ciclo completo:
pedido → plano → código → resultado → crítica → reflexão
"""

import json
from datetime import datetime
from pathlib import Path
from core.logger import get_logger

log = get_logger(__name__)


class TrainingLog:
    def __init__(self, cfg: dict):
        self.path = Path(cfg["paths"]["training_log"])

    def registrar(
        self,
        pedido: str,
        plano: list,
        codigo: str,
        sucesso: bool,
        erro: str = None,
        feedback_critico: dict = None,
        caminho_imagem: str = None,
    ) -> None:
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "pedido": pedido,
            "plano": plano,
            "codigo_gerado": codigo,
            "sucesso": sucesso,
            "erro": erro,
            "caminho_imagem": caminho_imagem,
            "feedback_critico": feedback_critico,
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
            nota = feedback_critico.get("nota_geral", "?") if feedback_critico else "-"
            log.debug(f"Tentativa registrada: '{pedido}' | sucesso={sucesso} | nota={nota}")
        except Exception as e:
            log.error(f"Falha ao registrar tentativa: {e}")