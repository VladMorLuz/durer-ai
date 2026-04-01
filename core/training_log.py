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
    ) -> None:
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "pedido": pedido,
            "plano": plano,
            "codigo_gerado": codigo,
            "sucesso": sucesso,
            "erro": erro,
            "feedback_critico": feedback_critico,
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
            log.debug(f"Tentativa registrada: '{pedido}' | sucesso={sucesso}")
        except Exception as e:
            log.error(f"Falha ao registrar tentativa: {e}")