"""
Uso:
    python main.py --check        → verifica se tudo está configurado
    python main.py --draw "..."   → executa um pedido de desenho
"""

import sys
import argparse
from core.config import load_config
from core.logger import get_logger
from core.llm import LLMClient
from core.training_log import TrainingLog
from drawing.krita_bridge import KritaBridge
from drawing.agent import DrawingAgent
from drawing.renderer import Renderer


def check_setup(cfg: dict, log) -> bool:
    ok = True

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

    log.info("Verificando conexão com Krita...")
    bridge = KritaBridge(cfg)
    if bridge.ping():
        log.info("Krita bridge: OK")
    else:
        log.warning(
            "Krita não encontrado — abra o Krita e certifique-se "
            "que o plugin Dürer Server está ativo."
        )

    return ok


def executar_desenho(pedido: str, cfg: dict, log) -> bool:
    """Loop completo B+C com registro: pedido → plano → código → Krita → log."""

    bridge = KritaBridge(cfg)
    if not bridge.ping():
        log.error("Krita não está acessível. Abra o Krita antes de desenhar.")
        return False

    tlog = TrainingLog(cfg)

    # Estágio 1: plano de intenções
    agent = DrawingAgent(cfg)
    plano = agent.plan(pedido)

    if not plano:
        log.error("Não foi possível gerar o plano de desenho.")
        tlog.registrar(
            pedido=pedido,
            plano=[],
            codigo="",
            sucesso=False,
            erro="Falha ao gerar plano de intenções",
        )
        return False

    # Estágio 2: renderização
    renderer = Renderer(cfg)
    resultado = renderer.render(plano)

    # Registra tudo no training log
    tlog.registrar(
        pedido=pedido,
        plano=plano,
        codigo=resultado["codigo"],
        sucesso=resultado["sucesso"],
        erro=resultado.get("erro"),
    )

    if resultado["sucesso"]:
        log.info(f"Desenho concluído: '{pedido}'")
    else:
        log.error(f"Falha ao desenhar: '{pedido}' — {resultado.get('erro')}")

    return resultado["sucesso"]


def main():
    parser = argparse.ArgumentParser(description="Dürer AI")
    parser.add_argument("--check", action="store_true",
                        help="Verifica configuração")
    parser.add_argument("--draw", type=str, metavar="PEDIDO",
                        help="Executa um pedido de desenho")
    args = parser.parse_args()

    try:
        cfg = load_config()
    except (FileNotFoundError, EnvironmentError) as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

    log = get_logger("main", cfg)
    log.info("=" * 50)
    log.info("Dürer AI")
    log.info("=" * 50)

    if args.check:
        ok = check_setup(cfg, log)
        if ok:
            log.info("✓ Setup completo.")
        else:
            log.error("✗ Problemas encontrados.")
            sys.exit(1)

    elif args.draw:
        ok = executar_desenho(args.draw, cfg, log)
        sys.exit(0 if ok else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()