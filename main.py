"""
Dürer AI — Ponto de entrada principal.

Uso:
    python main.py          → inicia o sistema completo
    python main.py --check  → só verifica se tudo está configurado
"""

import sys
import argparse
from core.config import load_config
from core.logger import get_logger
from core.llm import LLMClient
from drawing.krita_bridge import KritaBridge


def check_setup(cfg: dict, log) -> bool:
    """Verifica se todas as peças estão no lugar antes de iniciar."""
    ok = True

    # 1. Testa conexão com o Groq
    log.info("Verificando conexão com Groq...")
    try:
        llm = LLMClient(cfg)
        resposta = llm.chat(
            system="Você é o Dürer AI. Responda apenas: 'Sistema OK'.",
            user="ping",
        )
        log.info(f"Groq respondeu: {resposta.strip()}")
    except Exception as e:
        log.error(f"Falha na conexão com Groq: {e}")
        ok = False

    # 2. Testa conexão com o Krita
    log.info("Verificando conexão com Krita...")
    bridge = KritaBridge(cfg)
    krita_ok = bridge.ping()
    if not krita_ok:
        log.warning(
            "Krita não encontrado — não é um erro fatal na Fase 1. "
            "Abra o Krita e ative o plugin de servidor para as próximas fases."
        )
        # Não marca como falha — Krita é opcional na Fase 1

    return ok


def main():
    parser = argparse.ArgumentParser(description="Dürer AI")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica configuração sem iniciar o sistema completo",
    )
    args = parser.parse_args()

    # Carrega config (valida .env + config.yaml)
    try:
        cfg = load_config()
    except (FileNotFoundError, EnvironmentError) as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

    log = get_logger("main", cfg)
    log.info("=" * 50)
    log.info("Dürer AI iniciando...")
    log.info("=" * 50)

    if args.check or True:  # Na Fase 1, sempre roda o check
        tudo_ok = check_setup(cfg, log)
        if tudo_ok:
            log.info("✓ Setup completo. Pronto para a Fase 2.")
        else:
            log.error("✗ Problemas encontrados. Corrija antes de continuar.")
            sys.exit(1)


if __name__ == "__main__":
    main()
