"""
Dürer AI — Métricas computacionais do desenho.
Análise objetiva antes de chamar o Gemini.
Usa apenas Pillow — sem API.
"""

from pathlib import Path
from PIL import Image, ImageStat
from core.logger import get_logger

log = get_logger(__name__)


def analisar(caminho_imagem: Path) -> dict:
    """
    Calcula métricas objetivas da imagem.
    Retorna um dict com os dados — passado como contexto pro Gemini.
    """
    try:
        img = Image.open(caminho_imagem).convert("RGBA")
        w, h = img.size

        # Cobertura: % de pixels não-brancos (área desenhada)
        rgb = img.convert("RGB")
        pixels = list(rgb.getdata())
        nao_brancos = sum(1 for r, g, b in pixels if not (r > 240 and g > 240 and b > 240))
        cobertura = round(nao_brancos / len(pixels) * 100, 2)

        # Distribuição: onde estão os pixels desenhados (quadrantes)
        largura_q = w // 2
        altura_q = h // 2
        quadrantes = {"superior_esq": 0, "superior_dir": 0,
                      "inferior_esq": 0, "inferior_dir": 0}
        for i, (r, g, b) in enumerate(pixels):
            if r > 240 and g > 240 and b > 240:
                continue
            x = i % w
            y = i // w
            q = ("superior" if y < altura_q else "inferior") + \
                "_" + ("esq" if x < largura_q else "dir")
            quadrantes[q] += 1

        total_desenhado = max(nao_brancos, 1)
        distribuicao = {k: round(v / total_desenhado * 100, 1)
                        for k, v in quadrantes.items()}

        # Complexidade: desvio padrão dos canais (mais variação = mais complexo)
        stat = ImageStat.Stat(rgb)
        complexidade = round(sum(stat.stddev) / 3, 2)

        # Uso do espaço: bounding box do conteúdo vs canvas total
        bbox = rgb.convert("L").point(lambda p: 0 if p > 240 else 255)
        caixa = bbox.getbbox()
        if caixa:
            bw = caixa[2] - caixa[0]
            bh = caixa[3] - caixa[1]
            uso_espaco = round((bw * bh) / (w * h) * 100, 2)
            centralizacao_x = round((caixa[0] + bw / 2) / w * 100, 1)
            centralizacao_y = round((caixa[1] + bh / 2) / h * 100, 1)
        else:
            uso_espaco = 0.0
            centralizacao_x = 50.0
            centralizacao_y = 50.0

        metricas = {
            "resolucao": f"{w}x{h}",
            "cobertura_pct": cobertura,
            "uso_espaco_pct": uso_espaco,
            "complexidade": complexidade,
            "centralizacao_x_pct": centralizacao_x,
            "centralizacao_y_pct": centralizacao_y,
            "distribuicao_quadrantes": distribuicao,
        }

        log.debug(f"Métricas: cobertura={cobertura}% | complexidade={complexidade}")
        return metricas

    except Exception as e:
        log.error(f"Erro ao analisar métricas: {e}")
        return {}


def resumo_legivel(metricas: dict) -> str:
    """Converte métricas em texto para passar como contexto ao Gemini."""
    if not metricas:
        return "Métricas indisponíveis."

    d = metricas.get("distribuicao_quadrantes", {})
    return (
        f"- Resolução: {metricas.get('resolucao')}\n"
        f"- Área desenhada: {metricas.get('cobertura_pct')}% do canvas\n"
        f"- Espaço ocupado pelo conteúdo: {metricas.get('uso_espaco_pct')}% do canvas\n"
        f"- Complexidade visual: {metricas.get('complexidade')} (escala 0-127)\n"
        f"- Centro do desenho: x={metricas.get('centralizacao_x_pct')}%, "
        f"y={metricas.get('centralizacao_y_pct')}% do canvas\n"
        f"- Distribuição: sup-esq={d.get('superior_esq')}% | "
        f"sup-dir={d.get('superior_dir')}% | "
        f"inf-esq={d.get('inferior_esq')}% | "
        f"inf-dir={d.get('inferior_dir')}%"
    )