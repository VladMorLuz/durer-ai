"""
Dürer AI — Renderer (Estágio 2 do B+C)
Recebe o plano de intenções e gera + executa código QPainter no Krita.
"""

import json
from core.llm import LLMClient
from core.logger import get_logger
from drawing.krita_bridge import KritaBridge

log = get_logger(__name__)

SYSTEM_PROMPT = """Você é o tradutor técnico do Dürer AI.
Recebe um plano de intenções artísticas e gera código Python com QPainter para executar no Krita.

Imports já disponíveis no contexto de execução (NÃO reimporte):
- QPainter, QColor, QPen, QPainterPath, QPoint, QRect, QRectF já estão importados
- A variável `painter` já existe e está pronta para uso
- A variável `W` é a largura do canvas em pixels
- A variável `H` é a altura do canvas em pixels

Regras:
- Use APENAS os objetos listados acima
- NÃO use import, NÃO redefina painter, W ou H
- Traduza regiões relativas para coordenadas absolutas usando W e H
- proporcao 0.5 = metade do canvas; use isso para calcular tamanhos
- Prefira linhas orgânicas com QPainterPath para formas naturais
- Sempre defina pen antes de desenhar: painter.setPen(QPen(QColor(0,0,0), espessura))
- Para preencher formas: use painter.setBrush(QColor(r,g,b)) antes de desenhar
- Para desenhar SEM preenchimento: use painter.setBrush(Qt.NoBrush) — importe Qt de PyQt5.QtCore
- Termine com: painter.end()

Responda APENAS com código Python válido, sem explicações, sem markdown, sem backticks."""


class Renderer:
    def __init__(self, cfg: dict):
        self.llm = LLMClient(cfg)
        self.bridge = KritaBridge(cfg)
        self.canvas_w = cfg["krita"]["canvas_width"]
        self.canvas_h = cfg["krita"]["canvas_height"]
        self._ultimo_codigo = ""

    def render(self, plano: list[dict]) -> dict:
        """
        Estágio 2: traduz o plano em código e executa no Krita.
        Retorna dict com: sucesso (bool), codigo (str), erro (str|None)
        """
        resultado = {"sucesso": False, "codigo": "", "erro": None}

        if not plano:
            resultado["erro"] = "Plano vazio"
            log.error(resultado["erro"])
            return resultado

        log.info("Gerando código QPainter a partir do plano...")

        prompt_plano = json.dumps(plano, ensure_ascii=False, indent=2)
        codigo = self.llm.chat(
            system=SYSTEM_PROMPT,
            user=(
                f"Canvas: {self.canvas_w}x{self.canvas_h} pixels\n\n"
                f"Plano de intenções:\n{prompt_plano}"
            )
        )

        codigo = _limpar_codigo(codigo)
        self._ultimo_codigo = codigo
        resultado["codigo"] = codigo
        log.debug(f"Código gerado:\n{codigo}")

        script = _montar_script(codigo, self.canvas_w, self.canvas_h)

        log.info("Enviando script para o Krita...")
        resposta = self.bridge.send_script(script)

        if resposta.get("ok"):
            resultado["sucesso"] = True
            log.info("Renderização concluída com sucesso")
        else:
            resultado["erro"] = resposta.get("error", "Erro desconhecido")
            log.error(f"Erro na renderização: {resultado['erro']}")

        return resultado


def _limpar_codigo(codigo: str) -> str:
    linhas = codigo.strip().splitlines()
    linhas = [l for l in linhas if not l.strip().startswith("```")]
    return "\n".join(linhas).strip()


def _montar_script(codigo_usuario: str, w: int, h: int) -> str:
    """
    Envolve o código gerado pelo LLM em try/except robusto.
    Erros são capturados e retornados como JSON — nunca crasham o Krita.
    """
    # Indenta o código do usuário para ficar dentro do try
    codigo_indentado = "\n".join(
        "    " + linha for linha in codigo_usuario.splitlines()
    )

    return f"""
from krita import Krita
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QBrush
from PyQt5.QtCore import QPoint, QRect, QRectF, Qt
from PyQt5.QtGui import QImage

app = Krita.instance()
doc = app.activeDocument()

if not doc:
    raise RuntimeError("Nenhum documento aberto no Krita")

node = doc.activeNode()
W = doc.width()
H = doc.height()

# Usa os pixels reais do layer (não thumbnail reduzido)
raw = node.pixelData(0, 0, W, H)
img = QImage(bytes(raw), W, H, W * 4, QImage.Format_ARGB32)

painter = QPainter(img)
painter.setRenderHint(QPainter.Antialiasing)

try:
{codigo_indentado}
except Exception as _err:
    import sys
    print(f"[Dürer] Erro no código gerado: {{_err}}", file=sys.stderr)
finally:
    try:
        painter.end()
    except Exception:
        pass

node.setPixelData(
    bytes(img.bits().asarray(img.byteCount())),
    0, 0, W, H
)
doc.refreshProjection()
"""