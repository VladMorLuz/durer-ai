"""
Dürer AI — Crítico visual com Ollama local (Qwen2.5-VL 3B).
Combina visão multimodal local + métricas computacionais.
Sem API externa, sem custo, sem quota.
"""

import json
import base64
import time
from pathlib import Path
import urllib.request
import urllib.error
from critic import metrics
from core.logger import get_logger

log = get_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "moondream"

SYSTEM_CRITICO = """Você é o crítico artístico do Dürer AI — uma IA que está aprendendo a desenhar.
Seu papel é dar feedback construtivo e específico sobre os desenhos produzidos.

Você receberá:
1. O pedido original que a IA tentou executar
2. A imagem do desenho resultante
3. Métricas objetivas do desenho

Analise o desenho e responda APENAS com JSON válido neste formato exato:
{
  "nota_geral": 7,
  "o_que_funcionou": "descrição específica do que foi bem executado",
  "problemas": ["problema 1", "problema 2"],
  "sugestoes": ["sugestão concreta 1", "sugestão concreta 2"],
  "proxima_tentativa": "instrução direta do que tentar diferente",
  "conceitos_para_estudar": ["conceito 1", "conceito 2"]
}

Seja específico e construtivo. Esta IA está aprendendo — ajude-a a melhorar."""


class VisionCritic:
    def __init__(self, cfg: dict):
        self.model = OLLAMA_MODEL

    def ping(self) -> bool:
        """Verifica se o Ollama está rodando."""
        try:
            req = urllib.request.Request("http://localhost:11434")
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False

    def avaliar(self, pedido: str, caminho_imagem: Path) -> dict:
        """
        Avalia um desenho combinando visão local + métricas computacionais.
        Retorna dict com o feedback estruturado.
        """
        log.info(f"Avaliando desenho com Ollama ({self.model})...")

        # Métricas computacionais
        m = metrics.analisar(caminho_imagem)
        resumo_metricas = metrics.resumo_legivel(m)

        # Codifica imagem em base64
        img_b64 = _encode_imagem(caminho_imagem)
        if not img_b64:
            return _feedback_vazio("Não foi possível carregar a imagem")

        prompt = (
            f"Pedido original: '{pedido}'\n\n"
            f"Métricas objetivas:\n{resumo_metricas}\n\n"
            f"Analise a imagem e forneça feedback no formato JSON solicitado."
        )

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": SYSTEM_CRITICO + "\n\n" + prompt,
                    "images": [img_b64],
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1024,
            }
        }).encode("utf-8")

        for tentativa in range(3):
            try:
                log.info(f"  Enviando para Ollama (pode demorar 1-3 min)...")
                req = urllib.request.Request(
                    OLLAMA_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                # Timeout generoso — CPU pode demorar
                with urllib.request.urlopen(req, timeout=300) as resp:
                    resposta = json.loads(resp.read().decode("utf-8"))

                texto = resposta["message"]["content"]
                feedback = json.loads(_limpar_json(texto))
                feedback["metricas"] = m
                log.info(f"Avaliação concluída — nota: {feedback.get('nota_geral')}/10")
                return feedback

            except json.JSONDecodeError:
                log.warning("Ollama retornou JSON inválido — extraindo parcialmente")
                feedback = _extrair_feedback_parcial(texto)
                feedback["metricas"] = m
                return feedback

            except urllib.error.URLError as e:
                log.error(f"Ollama não acessível: {e}")
                if tentativa < 2:
                    log.info("Aguardando 10s e tentando novamente...")
                    time.sleep(10)
                else:
                    return _feedback_vazio("Ollama não está rodando. Execute: ollama serve")

            except Exception as e:
                log.error(f"Erro na avaliação: {e}")
                return _feedback_vazio(str(e))

        return _feedback_vazio("Falha após 3 tentativas")


def _encode_imagem(caminho: Path, max_size: int = 512) -> str | None:
    """
    Lê imagem, redimensiona para análise e retorna base64 string.
    O canvas original não é afetado — só a cópia enviada ao modelo.
    """
    try:
        from PIL import Image
        import io
        img = Image.open(caminho).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        log.error(f"Erro ao ler imagem: {e}")
        return None


def _limpar_json(texto: str) -> str:
    linhas = texto.strip().splitlines()
    linhas = [l for l in linhas if not l.strip().startswith("```")]
    # Encontra o primeiro { e último }
    texto_limpo = "\n".join(linhas)
    inicio = texto_limpo.find("{")
    fim = texto_limpo.rfind("}") + 1
    if inicio >= 0 and fim > inicio:
        return texto_limpo[inicio:fim]
    return texto_limpo


def _extrair_feedback_parcial(texto: str) -> dict:
    return {
        "nota_geral": 0,
        "o_que_funcionou": "Não foi possível avaliar",
        "problemas": ["Resposta do modelo inválida"],
        "sugestoes": [],
        "proxima_tentativa": "Tente novamente",
        "conceitos_para_estudar": [],
        "resposta_bruta": texto[:500],
    }


def _feedback_vazio(motivo: str) -> dict:
    return {
        "nota_geral": 0,
        "o_que_funcionou": "",
        "problemas": [motivo],
        "sugestoes": [],
        "proxima_tentativa": "",
        "conceitos_para_estudar": [],
        "metricas": {},
    }