"""
Dürer AI — Base de Conhecimento
Salva e recupera textos processados da knowledge_base/.
Cada arquivo vira um .txt com metadados no cabeçalho.
"""

from pathlib import Path
from datetime import datetime
from core.logger import get_logger

log = get_logger(__name__)


class KnowledgeStore:
    def __init__(self, cfg: dict):
        self.base = Path(cfg["paths"]["knowledge_base"])

    def salvar(self, nome_origem: str, texto: str, tipo: str) -> Path:
        """
        Salva texto extraído na knowledge_base.
        tipo: 'pdf' ou 'video'
        Retorna o caminho do arquivo salvo.
        """
        slug = Path(nome_origem).stem.replace(" ", "_").lower()
        caminho = self.base / f"{slug}.txt"

        cabecalho = (
            f"# Dürer AI — Knowledge Base\n"
            f"# Origem: {nome_origem}\n"
            f"# Tipo: {tipo}\n"
            f"# Processado em: {datetime.now().isoformat()}\n"
            f"# Caracteres: {len(texto)}\n"
            f"{'=' * 60}\n\n"
        )

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(cabecalho + texto)

        log.info(f"Conhecimento salvo: {caminho.name}")
        return caminho

    def ja_processado(self, nome_origem: str) -> bool:
        """Verifica se esse arquivo já foi processado anteriormente."""
        slug = Path(nome_origem).stem.replace(" ", "_").lower()
        return (self.base / f"{slug}.txt").exists()

    def listar(self) -> list[Path]:
        """Lista todos os arquivos na knowledge_base."""
        return sorted(self.base.glob("*.txt"))

    def ler(self, caminho: Path) -> str:
        """Lê o conteúdo de um arquivo da knowledge_base (sem o cabeçalho)."""
        texto = caminho.read_text(encoding="utf-8")
        separador = "=" * 60
        if separador in texto:
            return texto.split(separador, 1)[1].strip()
        return texto