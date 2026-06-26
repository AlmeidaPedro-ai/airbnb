# Gestão de Locação de Temporada (Airbnb — Rio de Janeiro)

Aplicação para gerenciar a locação de temporada de 2–3 apartamentos: métricas
**operacionais** (ocupação, vacância, diárias), **financeiras** (receita,
despesas por categoria, lucro) e **tributárias** (estimativa de IR via
Carnê-Leão), por apartamento e por período.

> **Estado atual: Fase 1 (Esqueleto) concluída.** Backend com modelos,
> migrações, seed e a lógica de cálculo isolada e 100% testada. API REST,
> frontend, importação/exportação e deploy chegam nas fases seguintes.

## Stack

- **Backend:** Python 3.12 (compatível 3.11) · FastAPI · SQLAlchemy 2.0 · Pydantic v2
- **Banco:** PostgreSQL · migrações com Alembic
- **Locale:** pt-BR · moeda R$ · datas `dd/mm/yyyy` · fuso `America/Sao_Paulo`

## Princípios

1. **Dinheiro nunca em `float`** — `Decimal` no Python, `NUMERIC(12,2)` no
   Postgres. Arredonda só na apresentação.
2. **Lógica de cálculo isolada** em `app/services/metrics.py` e
   `app/services/tax.py` — funções puras, sem banco/framework, testáveis com
   pytest.
3. **Toda regra tributária é parâmetro de banco** (`parametros_ir`), não
   constante no código.

## Estrutura

```
backend/
  app/
    config.py            # settings via env
    database.py          # engine/session/Base
    enums.py             # Canal, StatusReserva, CategoriaDespesa
    models.py            # modelos SQLAlchemy (NUMERIC(12,2) p/ dinheiro)
    seed_data.py         # dataset canônico da seção 11 (fonte única)
    seed.py              # popula o banco (idempotente)
    main.py              # FastAPI (Fase 1: só /api/health)
    services/
      domain.py          # dataclasses puras de domínio
      metrics.py         # KPIs operacionais/financeiros (puro)
      tax.py             # Carnê-Leão (puro)
      adapters.py        # ORM -> domínio
  alembic/               # migrações
  tests/                 # pytest (paridade com a planilha validada)
docker-compose.yml       # Postgres local
```

## Execução local

### 1. Subir o Postgres

```bash
docker compose up -d db
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # ajuste se necessário

# Migrar e popular com o dataset de exemplo (seção 11)
alembic upgrade head
python -m app.seed

# Subir a API (Fase 1: healthcheck em /api/health)
uvicorn app.main:app --reload
```

### 3. Testes

```bash
cd backend
pytest -q
```

Os testes validam **paridade exata com a planilha** (período 01/01–31/03/2026,
todos os apartamentos): 15 reservas, 69 noites, receita R$ 22.300,00, ADR
R$ 323,19, ocupação 25,6%, despesas R$ 8.510,00, imposto R$ 1.541,00 e lucro
líquido R$ 13.907,00.

## Regras de cálculo (resumo)

- **Proração por noite:** uma noite pertence à data em que se dorme; a noite do
  check-out não conta. Receita de reservas que cruzam o mês é alocada
  proporcionalmente (`valor * noites_no_periodo / noites_totais`).
- **Total de hóspedes:** soma apenas das reservas com *check-in* no período
  (evita contar em dobro reservas que cruzam meses).
- **Noites disponíveis:** `dias_no_periodo × nº de apartamentos`. Há flag
  opcional para respeitar `data_inicio_operacao` de cada apê (desligada por
  padrão, para manter paridade com a planilha).
- **Imposto (Carnê-Leão):** por CPF, somando todos os apartamentos no mês.
  Base = receita tributável + outras rendas − despesas dedutíveis. Sem desconto
  simplificado de 20% (regra de 2026).

> ⚠️ **A estimativa de IR não é orientação contábil.** Confirme alíquotas e
> deduções com seu contador.

### Discrepância documentada — faixa de transição 2026

A especificação descreve uma **faixa de transição** (R$ 5.000,01–7.350,00) com
redução parcial do imposto. Porém os **valores validados na planilha** (seção
11) tratam a isenção como um *penhasco*: isento até R$ 5.000 e **imposto cheio
acima disso**, sem redução — ex.: base R$ 5.750 → imposto R$ 685,25 (= imposto
bruto integral).

Para honrar ambos, o redutor de transição é **configurável** via
`ParametrosIR.aplicar_redutor_transicao` (coluna no banco), **desligado por
padrão** — assim os testes de aceite passam. Quando ligado, aplica uma
interpolação linear (marcada com `# TODO: confirmar fórmula do redutor 2026 com
contador/Receita`). Defina qual comportamento é o correto fiscalmente e eu ajusto
o default.

## Roadmap

- [x] **Fase 1 — Esqueleto:** modelos, migrações, seed, cálculo + testes.
- [ ] **Fase 2 — API:** endpoints REST, autenticação JWT, OpenAPI.
- [ ] **Fase 3 — Frontend:** dashboard, gráficos, CRUDs.
- [ ] **Fase 4 — Importação/Exportação CSV.**
- [ ] **Fase 5 — Deploy Railway:** Dockerfile, env, migrações no start.
