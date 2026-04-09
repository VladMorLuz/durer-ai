"""
Dürer AI — Ponto de entrada principal.

Uso:
    python main.py --check          → verifica se tudo está configurado
    python main.py --draw "..."     → executa um pedido de desenho
    python main.py --study          → processa novos arquivos em input/
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
from drawing.canvas_export import CanvasExporter
from critic.vision import VisionCritic
from critic.post_report import PostReportGenerator
from ingestion.pipeline import IngestionPipeline


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

    log.info("Verificando Ollama (visão local)...")
    critic = VisionCritic(cfg)
    if critic.ping():
        log.info("Ollama: OK")
    else:
        log.warning(
            "Ollama não está rodando. "
            "Execute 'ollama serve' em outro terminal antes de desenhar."
        )

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
    """Loop completo: pedido → plano → desenho → export → crítica → reflexão → log."""

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
        tlog.registrar(pedido=pedido, plano=[], codigo="",
                       sucesso=False, erro="Falha ao gerar plano")
        return False

    # Estágio 2: renderização
    renderer = Renderer(cfg)
    resultado = renderer.render(plano)

    if not resultado["sucesso"]:
        tlog.registrar(
            pedido=pedido, plano=plano,
            codigo=resultado["codigo"],
            sucesso=False, erro=resultado.get("erro"),
        )
        log.error(f"Falha ao desenhar: '{pedido}' — {resultado.get('erro')}")
        return False

    # Estágio 3: exporta canvas
    log.info("Exportando canvas para análise...")
    slug = pedido[:30].replace(" ", "_").lower()
    exporter = CanvasExporter(cfg)
    caminho_img = exporter.exportar(slug)

    feedback = {}
    caminho_img_str = None

    if caminho_img:
        caminho_img_str = str(caminho_img)

        # Estágio 4: crítica visual (Ollama local)
        critic = VisionCritic(cfg)
        if critic.ping():
            feedback = critic.avaliar(pedido, caminho_img)
        else:
            log.warning("Ollama não disponível — crítica pulada. Execute 'ollama serve'.")

        # Estágio 5: relatório pós-desenho
        if feedback:
            reporter = PostReportGenerator(cfg)
            reporter.gerar(pedido, plano, feedback)
    else:
        log.warning("Canvas não exportado — crítica pulada")

    # Registra tudo no training log
    tlog.registrar(
        pedido=pedido,
        plano=plano,
        codigo=resultado["codigo"],
        sucesso=True,
        caminho_imagem=caminho_img_str,
        feedback_critico=feedback if feedback else None,
    )

    nota = feedback.get("nota_geral", "?") if feedback else "sem crítica"
    log.info(f"Desenho concluído: '{pedido}' | nota: {nota}/10")
    return True


def executar_estudo(cfg: dict, log) -> None:
    log.info("Iniciando pipeline de ingestão...")
    pipeline = IngestionPipeline(cfg)
    total = pipeline.processar_novos()

    if total == 0:
        log.info("Nenhum arquivo novo para processar.")
        log.info("Coloque PDFs ou vídeos na pasta input/ e rode novamente.")
    else:
        log.info(f"Estudo concluído. {total} arquivo(s) processado(s).")
        log.info("Relatórios salvos em reports/ | Textos em knowledge_base/")


def main():
    parser = argparse.ArgumentParser(description="Dürer AI")
    parser.add_argument("--check", action="store_true",
                        help="Verifica configuração")
    parser.add_argument("--draw", type=str, metavar="PEDIDO",
                        help="Executa um pedido de desenho com crítica")
    parser.add_argument("--study", action="store_true",
                        help="Processa novos arquivos em input/")
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
        log.info("✓ Setup completo." if ok else "Verifique os avisos acima.")

    elif args.draw:
        ok = executar_desenho(args.draw, cfg, log)
        sys.exit(0 if ok else 1)

    elif args.study:
        executar_estudo(cfg, log)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()