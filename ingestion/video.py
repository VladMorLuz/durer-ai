"""
Dürer AI — Ingestão de Vídeos
Extrai áudio com ffmpeg e transcreve via Whisper (Groq API).
"""

import subprocess
import tempfile
from pathlib import Path
from groq import Groq
from core.logger import get_logger

log = get_logger(__name__)

FORMATOS_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}


def extrair_texto(caminho: Path, api_key: str) -> str:
    """
    Extrai áudio do vídeo e transcreve via Whisper no Groq.
    Retorna a transcrição como string, ou "" em caso de falha.
    """
    if caminho.suffix.lower() not in FORMATOS_VIDEO:
        log.warning(f"Formato não suportado: {caminho.suffix}")
        return ""

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        caminho_audio = Path(tmp.name)

    try:
        # Extrai áudio com ffmpeg
        log.info(f"Extraindo áudio de: {caminho.name}")
        resultado = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(caminho),
                "-vn",                  # sem vídeo
                "-ar", "16000",         # 16kHz — ideal pro Whisper
                "-ac", "1",             # mono
                "-q:a", "0",
                str(caminho_audio),
            ],
            capture_output=True,
            timeout=300,
        )
        if resultado.returncode != 0:
            log.error(f"ffmpeg falhou: {resultado.stderr.decode()}")
            return ""

        # Verifica tamanho — Groq aceita até 25MB
        tamanho_mb = caminho_audio.stat().st_size / (1024 * 1024)
        if tamanho_mb > 25:
            log.warning(f"Áudio muito grande ({tamanho_mb:.1f}MB) — Groq aceita até 25MB")
            log.warning("Considere usar vídeos mais curtos ou dividir o arquivo")
            return ""

        # Transcreve via Groq Whisper
        log.info(f"Transcrevendo ({tamanho_mb:.1f}MB)...")
        client = Groq(api_key=api_key)
        with open(caminho_audio, "rb") as audio:
            transcricao = client.audio.transcriptions.create(
                file=(caminho_audio.name, audio),
                model="whisper-large-v3",
                response_format="text",
            )

        log.info(f"Vídeo transcrito: {caminho.name} ({len(transcricao)} chars)")
        return transcricao

    except subprocess.TimeoutExpired:
        log.error(f"Timeout ao extrair áudio de {caminho.name}")
        return ""
    except Exception as e:
        log.error(f"Falha ao transcrever {caminho.name}: {e}")
        return ""
    finally:
        caminho_audio.unlink(missing_ok=True)