import json
from core.llm import LLMClient
from core.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """Você é o planejador artístico do Dürer AI.
Recebe um pedido de desenho e produz um plano de intenções artísticas em JSON.

Regras:
- Pense como um artista, não como uma calculadora
- Descreva INTENÇÕES, não coordenadas
- Divida o desenho em etapas lógicas (contorno primeiro, detalhes depois)
- Use regiões relativas: centro, superior, inferior, esquerda, direita, superior-esquerda, etc.
- Formas disponíveis: oval, circulo, retangulo, linha, amêndoa, arco, curva, triangulo, poligono
- proporcao: valor entre 0.1 (pequeno) e 0.9 (grande) relativo ao canvas
- espessura: valor entre 1 (fino) e 20 (grosso)
- Se o pedido incluir cor, adicione o campo "cor" com valor em formato [R, G, B]
- Se o pedido incluir preenchimento, adicione "preenchimento": true e "cor_preenchimento": [R, G, B]

Responda APENAS com JSON válido, sem texto adicional, sem markdown, sem backticks.

Formato obrigatório:
[
  {
    "etapa": 1,
    "descricao": "descrição da intenção artística",
    "forma": "nome da forma",
    "regiao": "região do canvas",
    "proporcao": 0.4,
    "espessura": 2,
    "cor": [0, 0, 0],
    "preenchimento": false
  }
]"""


class DrawingAgent:
    def __init__(self, cfg: dict):
        self.llm = LLMClient(cfg)
        self.canvas_w = cfg["krita"]["canvas_width"]
        self.canvas_h = cfg["krita"]["canvas_height"]
        self._ultimo_plano = []

    def plan(self, pedido: str) -> list[dict]:
        """
        Estágio 1: transforma o pedido em plano de intenções.
        Retorna lista de etapas ou [] em caso de falha.
        """
        log.info(f"Planejando desenho: '{pedido}'")

        resposta = self.llm.chat(
            system=SYSTEM_PROMPT,
            user=f"Pedido de desenho: {pedido}\nCanvas: {self.canvas_w}x{self.canvas_h} pixels"
        )

        try:
            plano = json.loads(resposta)
            self._ultimo_plano = plano
            log.info(f"Plano gerado com {len(plano)} etapas")
            for etapa in plano:
                log.debug(f"  Etapa {etapa['etapa']}: {etapa['descricao']}")
            return plano
        except json.JSONDecodeError as e:
            log.error(f"LLM retornou JSON inválido: {e}")
            log.debug(f"Resposta bruta: {resposta}")
            return []