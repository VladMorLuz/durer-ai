"""
Dürer AI — Gerador de Relatórios
Leitura rápida para conteúdos curtos, aprofundada para longos.
Threshold: 8000 chars. Acima disso, 3 passagens com checkpoint e sleep anti-rate-limit.
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from core.llm import LLMClient
from core.logger import get_logger

log = get_logger(__name__)

THRESHOLD_APROFUNDADO = 8000
CHUNK_SIZE = 6000
SLEEP_ENTRE_CHAMADAS = 8  # segundos — mantém abaixo do TPM do Groq free tier

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_RAPIDO = """Você é o Dürer AI — uma inteligência artificial aprendendo a desenhar.
Você acabou de estudar um material sobre arte e técnicas de desenho.

Escreva um relatório de estudo em primeira pessoa, como um artista refletindo sobre o que aprendeu.
O relatório deve ter:
1. O que foi estudado (resumo do conteúdo)
2. Conceitos mais importantes identificados
3. Técnicas ou princípios úteis para aprender a desenhar
4. O que você quer tentar praticar
5. Dúvidas ou pontos que precisam de mais estudo

Escreva de forma reflexiva e genuína. Seja específico."""

SYSTEM_PASSAGEM1 = """Você é o Dürer AI analisando um material longo sobre arte.
Sua tarefa é identificar a estrutura do conteúdo.

Leia o texto e identifique os tópicos principais.
Responda APENAS com JSON válido, sem markdown, sem explicações.

Formato:
[
  {
    "topico": "Nome curto do tópico",
    "descricao": "O que é abordado (1-2 frases)",
    "inicio": 0,
    "fim": 1500
  }
]

"inicio" e "fim" são índices de caracteres no texto original.
Identifique entre 4 e 8 tópicos. Cubra todo o conteúdo."""

SYSTEM_PASSAGEM2 = """Você é o Dürer AI estudando um trecho específico de um material sobre arte.
Escreva uma reflexão aprofundada sobre este trecho em primeira pessoa.

Inclua:
- O que este trecho ensina especificamente
- Técnicas ou conceitos concretos mencionados
- Como isso se aplica ao aprendizado de desenho
- O que você quer praticar a partir disso

Seja específico. Este é seu diário de estudos."""

SYSTEM_PASSAGEM3 = """Você é o Dürer AI sintetizando um estudo completo sobre arte.
Você refletiu sobre cada parte de um material extenso.
Escreva o relatório final de síntese em primeira pessoa.

O relatório deve ter:
1. Visão geral do que foi aprendido
2. Os 5 conceitos mais importantes (com explicação)
3. Técnicas concretas que você quer praticar e em que ordem
4. Como este material muda sua abordagem ao desenho
5. Perguntas que surgiram e merecem mais investigação

Escreva como um artista que passou horas estudando — reflexivo, específico, com voz própria."""


class ReportGenerator:
    def __init__(self, cfg: dict):
        self.llm = LLMClient(cfg)
        self.reports_dir = Path(cfg["paths"]["reports"])

    def gerar(self, nome_origem: str, texto: str) -> Path:
        if len(texto) <= THRESHOLD_APROFUNDADO:
            log.info(f"Leitura rápida ({len(texto)} chars)")
            conteudo = self._leitura_rapida(nome_origem, texto)
            modo = "rapida"
        else:
            log.info(
                f"Leitura aprofundada ({len(texto)} chars) — 3 passagens. "
                f"Pode demorar alguns minutos."
            )
            conteudo = self._leitura_aprofundada(nome_origem, texto)
            modo = "aprofundada"

        return self._salvar(nome_origem, conteudo, modo)

    # ── Leitura rápida ────────────────────────────────────────────────────────

    def _leitura_rapida(self, nome: str, texto: str) -> str:
        texto_truncado = texto[:6000]
        if len(texto) > 6000:
            texto_truncado += "\n\n[... conteúdo truncado ...]"
        return self._chamar_llm(
            system=SYSTEM_RAPIDO,
            user=f"Material: {nome}\n\nConteúdo:\n{texto_truncado}"
        )

    # ── Leitura aprofundada ───────────────────────────────────────────────────

    def _leitura_aprofundada(self, nome: str, texto: str) -> str:
        checkpoint = self._carregar_checkpoint(nome)

        # Passagem 1: identifica tópicos (pula se já tiver checkpoint)
        if "topicos" in checkpoint:
            topicos = checkpoint["topicos"]
            log.info(f"Checkpoint: {len(topicos)} tópicos recuperados")
        else:
            log.info("Passagem 1/3 — identificando tópicos...")
            amostra = texto[:12000]
            resposta = self._chamar_llm(
                system=SYSTEM_PASSAGEM1,
                user=f"Material: {nome}\n\nTexto:\n{amostra}"
            )
            try:
                topicos = json.loads(_limpar_json(resposta))
                log.info(f"  {len(topicos)} tópicos identificados")
            except Exception as e:
                log.warning(f"Falha ao parsear tópicos ({e}) — usando chunks fixos")
                topicos = _chunks_fixos(texto)
            checkpoint["topicos"] = topicos
            self._salvar_checkpoint(nome, checkpoint)

        # Passagem 2: estuda cada tópico (pula os já feitos)
        if "reflexoes" not in checkpoint:
            checkpoint["reflexoes"] = {}

        reflexoes_prontas = checkpoint["reflexoes"]
        log.info("Passagem 2/3 — estudando cada tópico...")

        for i, topico in enumerate(topicos):
            chave = str(i)
            if chave in reflexoes_prontas:
                log.info(f"  Tópico {i+1}/{len(topicos)}: '{topico.get('topico')}' (checkpoint)")
                continue

            log.info(f"  Tópico {i+1}/{len(topicos)}: '{topico.get('topico')}'")
            inicio = topico.get("inicio", 0)
            fim = topico.get("fim", inicio + CHUNK_SIZE)
            trecho = texto[inicio:fim]

            if not trecho.strip():
                continue

            reflexao = self._chamar_llm(
                system=SYSTEM_PASSAGEM2,
                user=(
                    f"Material: {nome}\n"
                    f"Tópico: {topico.get('topico', '')}\n"
                    f"Descrição: {topico.get('descricao', '')}\n\n"
                    f"Trecho:\n{trecho}"
                )
            )
            reflexoes_prontas[chave] = {
                "titulo": topico.get("topico", f"Tópico {i+1}"),
                "reflexao": reflexao,
            }
            checkpoint["reflexoes"] = reflexoes_prontas
            self._salvar_checkpoint(nome, checkpoint)

        # Passagem 3: síntese final (pula se já tiver)
        if "sintese" in checkpoint:
            log.info("Passagem 3/3 — síntese recuperada do checkpoint")
            sintese = checkpoint["sintese"]
        else:
            log.info("Passagem 3/3 — sintetizando...")
            partes_reflexao = [
                f"### {v['titulo']}\n\n{v['reflexao']}"
                for v in reflexoes_prontas.values()
            ]
            resumo = "\n\n---\n\n".join(partes_reflexao)
            if len(resumo) > 10000:
                resumo = resumo[:10000] + "\n\n[... reflexões truncadas ...]"

            sintese = self._chamar_llm(
                system=SYSTEM_PASSAGEM3,
                user=(
                    f"Material estudado: {nome}\n\n"
                    f"Minhas reflexões por tópico:\n\n{resumo}"
                )
            )
            checkpoint["sintese"] = sintese
            self._salvar_checkpoint(nome, checkpoint)

        # Monta documento final
        reflexoes_lista = [
            f"### {v['titulo']}\n\n{v['reflexao']}"
            for v in reflexoes_prontas.values()
        ]
        conteudo = (
            "## Síntese Final\n\n" + sintese +
            "\n\n---\n\n## Reflexões por Tópico\n\n" +
            "\n\n---\n\n".join(reflexoes_lista)
        )

        # Limpa checkpoint após conclusão
        self._apagar_checkpoint(nome)
        return conteudo

    # ── LLM com sleep anti-rate-limit ────────────────────────────────────────

    def _chamar_llm(self, system: str, user: str, tentativas: int = 3) -> str:
        for tentativa in range(tentativas):
            try:
                resposta = self.llm.chat(system=system, user=user)
                # Sleep após cada chamada bem-sucedida
                time.sleep(SLEEP_ENTRE_CHAMADAS)
                return resposta
            except Exception as e:
                erro = str(e)
                if "rate_limit" in erro or "429" in erro:
                    espera = 30 + (tentativa * 15)
                    log.warning(
                        f"Rate limit atingido — aguardando {espera}s "
                        f"(tentativa {tentativa+1}/{tentativas})"
                    )
                    time.sleep(espera)
                else:
                    log.error(f"Erro LLM: {e}")
                    raise
        raise RuntimeError(f"Falha após {tentativas} tentativas")

    # ── Checkpoint ────────────────────────────────────────────────────────────

    def _caminho_checkpoint(self, nome: str) -> Path:
        slug = _slugify(nome)
        return self.reports_dir / f"_checkpoint_{slug}.json"

    def _carregar_checkpoint(self, nome: str) -> dict:
        caminho = self._caminho_checkpoint(nome)
        if caminho.exists():
            try:
                dados = json.loads(caminho.read_text(encoding="utf-8"))
                log.info(f"Checkpoint encontrado — retomando de onde parou")
                return dados
            except Exception:
                pass
        return {}

    def _salvar_checkpoint(self, nome: str, dados: dict) -> None:
        caminho = self._caminho_checkpoint(nome)
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _apagar_checkpoint(self, nome: str) -> None:
        caminho = self._caminho_checkpoint(nome)
        if caminho.exists():
            caminho.unlink()

    # ── Salvar relatório ──────────────────────────────────────────────────────

    def _salvar(self, nome_origem: str, conteudo: str, modo: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(nome_origem)
        caminho = self.reports_dir / f"{timestamp}_{slug}.md"

        cabecalho = (
            f"# Relatório de Estudo — Dürer AI\n"
            f"**Material:** {nome_origem}\n"
            f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"**Modo:** "
            f"{'Leitura aprofundada (3 passagens)' if modo == 'aprofundada' else 'Leitura rápida'}\n\n"
            f"---\n\n"
        )

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(cabecalho + conteudo)

        log.info(f"Relatório salvo: {caminho.name}")
        return caminho


# ── Helpers ───────────────────────────────────────────────────────────────────

def _limpar_json(texto: str) -> str:
    linhas = texto.strip().splitlines()
    linhas = [l for l in linhas if not l.strip().startswith("```")]
    return "\n".join(linhas).strip()


def _chunks_fixos(texto: str) -> list[dict]:
    chunks = []
    i = 0
    n = 1
    while i < len(texto):
        fim = min(i + CHUNK_SIZE, len(texto))
        chunks.append({
            "topico": f"Parte {n}",
            "descricao": "Trecho sequencial do conteúdo",
            "inicio": i,
            "fim": fim,
        })
        i = fim
        n += 1
    return chunks


def _slugify(nome: str) -> str:
    stem = Path(nome).stem
    slug = re.sub(r'[^\w\s-]', '', stem).strip()
    slug = re.sub(r'[\s_]+', '_', slug)
    return slug[:60]