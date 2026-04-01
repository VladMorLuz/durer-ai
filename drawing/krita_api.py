import json
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KritaAPI:
    """
    Interface assíncrona com o Krita.
    Use como context manager para garantir que a conexão seja fechada.

    Exemplo:
        async with KritaAPI(host="localhost", port=9999) as krita:
            await krita.ping()
            await krita.draw_line(100, 100, 400, 400)
    """

    def __init__(self, host: str = "localhost", port: int = 9999):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self._ws = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    async def connect(self) -> None:
        """Estabelece conexão WebSocket com o Krita."""
        try:
            import websockets
            self._ws = await websockets.connect(self.uri)
            logger.info("Conectado ao Krita em %s", self.uri)
        except Exception as e:
            raise ConnectionError(
                f"Não foi possível conectar ao Krita em {self.uri}.\n"
                f"Verifique se o Krita está aberto e o plugin WebSocket está ativo.\n"
                f"Erro: {e}"
            )

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
            logger.info("Desconectado do Krita.")

    async def _send(self, command: dict) -> dict:
        """Envia um comando e aguarda resposta."""
        if not self._ws:
            raise RuntimeError("Não conectado ao Krita. Use 'async with KritaAPI()'.")
        payload = json.dumps(command)
        await self._ws.send(payload)
        response = await self._ws.recv()
        return json.loads(response)

    # ── Comandos básicos ──────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Testa a conexão. Retorna True se o Krita respondeu."""
        try:
            response = await self._send({"action": "ping"})
            ok = response.get("status") == "ok"
            if ok:
                logger.info("Ping ao Krita: OK")
            return ok
        except Exception as e:
            logger.error("Ping falhou: %s", e)
            return False

    async def new_canvas(self, width: int = 1920, height: int = 1080) -> bool:
        """Cria um novo documento em branco."""
        response = await self._send({
            "action": "new_canvas",
            "width": width,
            "height": height,
        })
        return response.get("status") == "ok"

    async def set_brush(self, brush_name: str, size: float = 10.0, opacity: float = 1.0) -> bool:
        """Seleciona e configura o pincel."""
        response = await self._send({
            "action": "set_brush",
            "brush_name": brush_name,
            "size": size,
            "opacity": opacity,
        })
        return response.get("status") == "ok"

    async def set_color(self, r: int, g: int, b: int, a: int = 255) -> bool:
        """Define a cor de pintura (valores 0-255)."""
        response = await self._send({
            "action": "set_color",
            "r": r, "g": g, "b": b, "a": a,
        })
        return response.get("status") == "ok"

    async def draw_stroke(self, points: list[tuple[float, float, float]]) -> bool:
        """
        Desenha um traço suave passando pelos pontos.
        Cada ponto é uma tupla (x, y, pressão) onde pressão vai de 0.0 a 1.0.
        """
        response = await self._send({
            "action": "draw_stroke",
            "points": [{"x": p[0], "y": p[1], "pressure": p[2]} for p in points],
        })
        return response.get("status") == "ok"

    async def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                        pressure: float = 0.8) -> bool:
        """Atalho para desenhar uma linha reta entre dois pontos."""
        return await self.draw_stroke([
            (x1, y1, pressure),
            (x2, y2, pressure),
        ])

    async def new_layer(self, name: str = "layer") -> bool:
        """Adiciona uma nova camada."""
        response = await self._send({
            "action": "new_layer",
            "name": name,
        })
        return response.get("status") == "ok"

    async def save_canvas(self, output_path: str) -> bool:
        """Salva o canvas atual como PNG."""
        response = await self._send({
            "action": "save_canvas",
            "path": output_path,
        })
        ok = response.get("status") == "ok"
        if ok:
            logger.info("Canvas salvo em: %s", output_path)
        return ok

    async def clear_canvas(self) -> bool:
        """Limpa o canvas (apaga tudo)."""
        response = await self._send({"action": "clear_canvas"})
        return response.get("status") == "ok"

    # ── Modo simulado (para testes sem Krita aberto) ──────────────────────────

    @classmethod
    def mock(cls) -> "KritaAPIMock":
        """Retorna uma versão simulada da API para testes."""
        return KritaAPIMock()


class KritaAPIMock:
    """
    Versão simulada do KritaAPI para rodar e testar o resto
    do sistema sem precisar do Krita aberto.
    Registra tudo no log em vez de executar de verdade.
    """

    async def __aenter__(self):
        logger.warning("KritaAPI rodando em modo SIMULADO (mock). Nenhum desenho real será feito.")
        return self

    async def __aexit__(self, *args):
        pass

    async def ping(self) -> bool:
        logger.info("[MOCK] ping -> ok")
        return True

    async def new_canvas(self, **kwargs) -> bool:
        logger.info("[MOCK] new_canvas %s", kwargs)
        return True

    async def set_brush(self, **kwargs) -> bool:
        logger.info("[MOCK] set_brush %s", kwargs)
        return True

    async def set_color(self, **kwargs) -> bool:
        logger.info("[MOCK] set_color %s", kwargs)
        return True

    async def draw_stroke(self, points, **kwargs) -> bool:
        logger.info("[MOCK] draw_stroke %d pontos", len(points))
        return True

    async def draw_line(self, x1, y1, x2, y2, **kwargs) -> bool:
        logger.info("[MOCK] draw_line (%s,%s) -> (%s,%s)", x1, y1, x2, y2)
        return True

    async def new_layer(self, **kwargs) -> bool:
        logger.info("[MOCK] new_layer %s", kwargs)
        return True

    async def save_canvas(self, output_path: str) -> bool:
        logger.info("[MOCK] save_canvas -> %s", output_path)
        return True

    async def clear_canvas(self) -> bool:
        logger.info("[MOCK] clear_canvas")
        return True
