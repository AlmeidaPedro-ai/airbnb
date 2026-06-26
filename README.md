# Gestão de Locação de Temporada (Airbnb — Rio de Janeiro)

Aplicação para gerenciar a locação de temporada de 2–3 apartamentos: métricas
**operacionais** (ocupação, vacância, diárias), **financeiras** (receita,
despesas por categoria, lucro) e **tributárias** (estimativa de IR via
Carnê-Leão), por apartamento e por período.

> **Estado atual: todas as fases (1–5) concluídas.** Backend + frontend
> completos, com importação/exportação CSV e **deploy no Railway** (Dockerfile
> único servindo API + frontend, Postgres gerenciado, migrações no start e
> healthcheck).

## Stack

- **Backend:** Python 3.12 (compatível 3.11) · FastAPI · SQLAlchemy 2.0 · Pydantic v2
- **Frontend:** React 18 · Vite · TypeScript · Recharts
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
    security.py          # hash bcrypt + JWT
    deps.py              # dependências (sessão, usuário autenticado)
    business.py          # regras que tocam o banco (sobreposição, etc.)
    schemas.py           # schemas Pydantic v2 (entrada/saída)
    main.py              # FastAPI: health + routers
    routers/             # auth, apartamentos, reservas, despesas,
                         #   metricas, imposto, parametros_ir
    services/
      domain.py          # dataclasses puras de domínio
      metrics.py         # KPIs operacionais/financeiros (puro)
      tax.py             # Carnê-Leão (puro)
      adapters.py        # ORM -> domínio
  alembic/               # migrações
  tests/                 # pytest (cálculo + integração da API)
frontend/
  src/
    api/                 # client HTTP (JWT) + tipos TS
    auth/                # contexto de autenticação
    components/          # Layout, Modal, hooks
    pages/               # Login, Dashboard, Reservas, Despesas,
                         #   Apartamentos, Imposto, ParametrosIR
    utils/format.ts      # formatação pt-BR (R$, datas, %)
docker-compose.yml       # Postgres local
```

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxy /api -> backend :8000)
npm run build    # type-check (tsc) + bundle de produção em dist/
```

Telas: **Dashboard** (filtros de apê/período com atalhos, 12 KPIs, gráficos de
ocupação, receita × despesas por mês e despesas por categoria, resumo por
apartamento), **Reservas/Despesas/Apartamentos** (CRUD com avisos de
capacidade/sobreposição e botões de exportação CSV/Excel), **Imposto** (grade
mensal com "outras rendas" editáveis, recálculo e exportação), **Importar CSV**
(upload → mapeamento de colunas → de-para de anúncios → dry-run → importação) e
**Parâmetros IR** (edição de faixas e isenção).

> Login com as credenciais de seed (abaixo). O backend precisa estar rodando.

## API REST

Documentação interativa (OpenAPI) em **`/docs`** com o servidor no ar. Todas as
rotas exigem JWT (`Authorization: Bearer <token>`), exceto `POST /api/auth/login`
e `GET /api/health`.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/login` | Login (email/senha) → access_token |
| GET | `/api/auth/me` | Usuário autenticado |
| GET/POST | `/api/apartamentos` | Listar/criar |
| GET/PUT/DELETE | `/api/apartamentos/{id}` | Obter/editar/excluir |
| GET/POST | `/api/reservas` | Listar (filtros `apartamento_id`,`inicio`,`fim`)/criar |
| GET/PUT/DELETE | `/api/reservas/{id}` | Obter/editar/excluir |
| GET/POST | `/api/despesas` | Listar (filtros apê/categoria/período)/criar |
| GET/PUT/DELETE | `/api/despesas/{id}` | Obter/editar/excluir |
| GET | `/api/metricas` | KPIs (`apartamento_id`,`inicio`,`fim`) |
| GET | `/api/metricas/por-apartamento` | KPIs por apê (`inicio`,`fim`) |
| GET | `/api/imposto?ano=` | Grade mensal + total anual |
| POST | `/api/imposto/calcular` | Recalcula a grade com "outras rendas" |
| GET/PUT | `/api/parametros-ir` | Ler/editar faixas e isenção |
| POST | `/api/importar/reservas/analisar` | Lê o CSV → colunas, mapeamento sugerido, anúncios |
| POST | `/api/importar/reservas/confirmar` | Dry-run ou importação efetiva |
| GET | `/api/exportar/{reservas\|despesas\|imposto}` | Exporta `formato=csv\|xlsx` |

**Credenciais de seed (dev):** email `1994.pedro@gmail.com`, senha `admin123`
(configuráveis via `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` antes do seed).
Troque em produção.

**Regras de negócio nas reservas:** `check_out > check_in` é bloqueante (422);
capacidade excedida e sobreposição de datas geram **avisos não bloqueantes** no
campo `avisos` da resposta de criação/edição.

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

## Deploy (Railway)

Imagem Docker **única** (`Dockerfile` na raiz): o estágio 1 builda o frontend
(Vite) e o estágio 2 (Python 3.12) instala o backend e serve a API **e** o build
estático do frontend na mesma origem — assim o `/api` funciona sem CORS/proxy e
há um só serviço para gerenciar.

### Passos no Railway

1. **New Project → Deploy from GitHub repo** (ou `railway up`). O Railway detecta
   o `Dockerfile`/`railway.json` automaticamente.
2. **Add → Database → PostgreSQL** (plugin gerenciado). Ele injeta `DATABASE_URL`
   no serviço — o app normaliza `postgres://` para `postgresql+psycopg://`.
3. **Variables** do serviço da API:
   - `JWT_SECRET` — segredo forte (obrigatório em produção).
   - `ENV=production`
   - `TZ=America/Sao_Paulo`
   - `SEED_ON_START=true` **apenas na primeira subida** (popula o dataset de
     exemplo; é idempotente). Depois remova ou deixe `false`.
   - `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` para criar o usuário inicial.
4. O **start** (`backend/start.sh`) roda `alembic upgrade head` e sobe o
   gunicorn (workers uvicorn) na porta `$PORT` do Railway.
5. **Healthcheck:** `railway.json` aponta para `/api/health`.

### Rodar a stack completa localmente (como no Railway)

```bash
docker compose up --build
# API + frontend: http://localhost:8000   (SEED_ON_START=true popula o exemplo)
```

> Variáveis: `DATABASE_URL`, `JWT_SECRET`, `ENV`, `TZ` (+ `SEED_ON_START`,
> `WEB_CONCURRENCY`). Ver `backend/.env.example`.

## Roadmap

- [x] **Fase 1 — Esqueleto:** modelos, migrações, seed, cálculo + testes.
- [x] **Fase 2 — API:** endpoints REST, autenticação JWT, OpenAPI.
- [x] **Fase 3 — Frontend:** dashboard, gráficos, CRUDs.
- [x] **Fase 4 — Importação/Exportação CSV.**
- [x] **Fase 5 — Deploy Railway:** Dockerfile, env, migrações no start, healthcheck.
