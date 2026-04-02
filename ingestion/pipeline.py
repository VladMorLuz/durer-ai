"""
Dürer AI — Pipeline de Ingestão
Varre a pasta input/, processa arquivos novos e gera conhecimento + relatórios.
"""

from pathlib import Path
from core.logger import get_logger
from ingestion import pdf, video
from knowledge.store import KnowledgeStore
from knowledge.report import ReportGenerator

log = get_logger(__name__)

FORMATOS_PDF = {".pdf"}
FORMATOS_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}


class IngestionPipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.input_dir = Path(cfg["paths"]["input"])
        self.store = KnowledgeStore(cfg)
        self.reporter = ReportGenerator(cfg)
        self.api_key = cfg["llm"]["api_key"]

    def processar_novos(self) -> int:
        """
        Varre input/ e processa apenas arquivos ainda não processados.
        Retorna quantos arquivos foram processados nessa rodada.
        """
        arquivos = [
            f for f in self.input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (FORMATOS_PDF | FORMATOS_VIDEO)
        ]

        if not arquivos:
            log.info("Nenhum arquivo encontrado em input/")
            return 0

        processados = 0
        for arquivo in arquivos:
            if self.store.ja_processado(arquivo.name):
                log.debug(f"Já processado, pulando: {arquivo.name}")
                continue

            log.info(f"Processando: {arquivo.name}")
            texto = self._extrair(arquivo)

            if not texto:
                log.warning(f"Nenhum texto extraído de: {arquivo.name}")
                continue

            # Salva na knowledge base
            self.store.salvar(arquivo.name, texto, self._tipo(arquivo))

            # Gera relatório de reflexão
            self.reporter.gerar(arquivo.name, texto)

            processados += 1
            log.info(f"Concluído: {arquivo.name}")

        return processados

    def _extrair(self, arquivo: Path) -> str:
        if arquivo.suffix.lower() in FORMATOS_PDF:
            return pdf.extrair_texto(arquivo)
        elif arquivo.suffix.lower() in FORMATOS_VIDEO:
            return video.extrair_texto(arquivo, self.api_key)
        return ""

    def _tipo(self, arquivo: Path) -> str:
        return "pdf" if arquivo.suffix.lower() in FORMATOS_PDF else "video"