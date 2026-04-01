# Dürer AI

Uma IA que aprende a desenhar — não gerando imagens, mas desenhando
manualmente no Krita, traço a traço, aprendendo por tentativa, erro e reflexão.

---

## Setup inicial

### 1. Ambiente Python
```bash
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Credenciais
```bash
cp .env.example .env
# Abra o .env e coloque sua GROQ_API_KEY
```

### 3. Verificar setup
```bash
python main.py --check
```

Se aparecer `✓ Setup completo`, está pronto para a Fase 2.

---

## Estrutura do projeto

```
dürer-ai/
├── core/               # Orquestrador, config, LLM, logger
├── ingestion/          # Leitura de PDFs e vídeos
├── knowledge/          # Base de conhecimento e relatórios
├── drawing/            # Agente de desenho + ponte com Krita
├── critic/             # Avaliação dos desenhos
│
├── input/              # Coloque aqui PDFs e vídeos para a IA estudar
├── knowledge_base/     # Textos processados (gerado automaticamente)
├── reports/            # Diários e reflexões da IA
├── outputs/            # Desenhos salvos
├── checkpoints/        # Snapshots do modelo
│
├── config.yaml         # Configuração central
├── .env                # Segredos (nunca vai pro git)
├── main.py             # Ponto de entrada
└── requirements.txt
```

---

## Fases do projeto

- [x] **Fase 1** — Esqueleto: estrutura, config, conexão com Groq e Krita
- [x] **Fase 2** — Loop mínimo: agente recebe pedido e traça no Krita
- [ ] **Fase 3** — Ingestão: IA lê PDFs/vídeos e escreve relatórios
- [ ] **Fase 4** — Crítico: avalia os desenhos com visão + métricas
- [ ] **Fase 5** — Modo autônomo: pratica sozinha em background
- [ ] **Fase 6** — Chat: interface para commissionar desenhos e dar feedback
