"""
Dürer AI — Exporta o canvas do Krita como PNG para análise.
Salva em outputs/ com timestamp para histórico.
"""

from pathlib import Path
from datetime import datetime
from drawing.krita_bridge import KritaBridge
from core.logger import get_logger

log = get_logger(__name__)


class CanvasExporter:
    def __init__(self, cfg: dict):
        self.bridge = KritaBridge(cfg)
        self.outputs_dir = Path(cfg["paths"]["outputs"])

    def exportar(self, slug: str = "") -> Path | None:
        """
        Manda o Krita salvar o canvas atual como PNG em outputs/.
        Retorna o caminho do arquivo salvo, ou None se falhar.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome = f"{timestamp}_{slug}.png" if slug else f"{timestamp}.png"
        caminho = self.outputs_dir / nome

        script = f"""
from krita import Krita
import os

app = Krita.instance()
doc = app.activeDocument()

if not doc:
    raise RuntimeError("Nenhum documento aberto")

doc.exportImage("{str(caminho).replace(chr(92), '/')}", app.exporters()[0])
"""
        resultado = self.bridge.send_script(script)

        if resultado.get("ok"):
            # Verifica se o arquivo foi realmente criado
            if caminho.exists():
                log.info(f"Canvas exportado: {caminho.name}")
                return caminho
            else:
                log.warning("Krita reportou sucesso mas arquivo não encontrado")
                return _exportar_fallback(self.bridge, caminho)
        else:
            log.warning(f"Exportação via Krita falhou: {resultado.get('error')}")
            return _exportar_fallback(self.bridge, caminho)


def _exportar_fallback(bridge: KritaBridge, caminho: Path) -> Path | None:
    """
    Fallback: captura os pixels via pixelData e salva com Pillow.
    Funciona mesmo se o exportador nativo do Krita falhar.
    """
    script = f"""
from krita import Krita
from PyQt5.QtGui import QImage

app = Krita.instance()
doc = app.activeDocument()
node = doc.activeNode()
W = doc.width()
H = doc.height()

raw = node.pixelData(0, 0, W, H)
img = QImage(bytes(raw), W, H, W * 4, QImage.Format_ARGB32)
img.save("{str(caminho).replace(chr(92), '/')}")
"""
    resultado = bridge.send_script(script)

    if resultado.get("ok") and caminho.exists():
        log.info(f"Canvas exportado (fallback): {caminho.name}")
        return caminho

    log.error("Falha ao exportar canvas")
    return None