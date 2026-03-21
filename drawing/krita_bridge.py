"""
Ponte entre o Dürer AI e o Krita.

Como funciona:
  O Krita tem um servidor de scripts Python embutido (Scripter / DBus).
  Esta classe gera scripts Python e os envia pro Krita via socket TCP
  usando o plugin "Simple Script Server" do Krita.

  Por enquanto (Fase 1), só testamos se a conexão funciona.
  Nas próximas fases, os métodos de desenho serão implementados aqui.
"""

import socket
import json
from core.logger import get_logger

log = get_logger(__name__)

KRITA_HOST = "127.0.0.1"
KRITA_PORT = 8888  # Porta padrão do servidor de scripts do Krita


class KritaBridge:
    def __init__(self, cfg: dict):
        self.host = KRITA_HOST
        self.port = KRITA_PORT
        self.cfg = cfg["krita"]

    def ping(self) -> bool:
        """
        Testa se o Krita está rodando e ouvindo na porta.
        Retorna True se conectou, False caso contrário.
        """
        try:
            with socket.create_connection((self.host, self.port), timeout=3):
                log.info("Krita bridge: conexão OK")
                return True
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            log.warning(f"Krita bridge: não foi possível conectar — {e}")
            log.warning(
                "Certifique-se que o Krita está aberto e o plugin "
                "de servidor de scripts está ativado."
            )
            return False

    def send_script(self, script: str) -> dict:
        """
        Envia um script Python pro Krita executar.
        Retorna {"ok": True} ou {"ok": False, "error": "..."}
        """
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as sock:
                payload = json.dumps({"script": script}) + "\n"
                sock.sendall(payload.encode("utf-8"))
                response = sock.recv(4096).decode("utf-8")
                return json.loads(response)
        except Exception as e:
            log.error(f"Erro ao enviar script pro Krita: {e}")
            return {"ok": False, "error": str(e)}
