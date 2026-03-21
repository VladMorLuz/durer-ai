"""
Carrega e valida config.yaml + .env
Qualquer módulo que precisar de configuração importa daqui.
Nunca leia config.yaml diretamente em outro arquivo.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env antes de qualquer coisa
load_dotenv()

_BASE_DIR = Path(__file__).parent.parent


def load_config() -> dict:
    config_path = _BASE_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml não encontrado em {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _inject_secrets(cfg)
    _resolve_paths(cfg)
    return cfg


def _inject_secrets(cfg: dict) -> None:
    """Injeta segredos do .env no config em memória (nunca em disco)."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise EnvironmentError(
            "GROQ_API_KEY não encontrada. "
            "Copie .env.example para .env e preencha sua chave."
        )
    cfg.setdefault("llm", {})["api_key"] = groq_key


def _resolve_paths(cfg: dict) -> None:
    """Converte paths relativos para absolutos a partir da raiz do projeto."""
    for key, val in cfg.get("paths", {}).items():
        absolute = _BASE_DIR / val
        cfg["paths"][key] = str(absolute)
        # Cria a pasta se não existir (exceto arquivos como state.db)
        if not absolute.suffix:
            absolute.mkdir(parents=True, exist_ok=True)
