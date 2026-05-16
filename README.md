# 📊 Finance Data Pipeline

> Pipeline de dados financeiros end-to-end com arquitetura moderna baseada em AWS, PostgreSQL e Python — projeto de portfólio profissional de Engenharia de Dados.

![Pipeline Rodando](docs/pipeline_ok.png)

---

## 🎯 O que é este projeto?

Este projeto simula um ambiente corporativo real de **Engenharia de Dados** para o mercado financeiro. Ele coleta automaticamente cotações diárias de ações americanas (Apple, Google, Microsoft, Amazon e Meta), armazena os dados brutos em um **Data Lake**, transforma e enriquece as informações, e carrega tudo em um **Data Warehouse** relacional para análises avançadas.

Os dados são visualizados em um **dashboard interativo** via Metabase, acessível pelo navegador.

---

## 🏗️ Arquitetura

```
Yahoo Finance API
       │
       ▼
  [ extract.py ]          ← Extração via yfinance (Python)
       │
       ├──► S3 Raw Layer  ← JSON particionado por ano/mês/dia
       │    s3://bucket/raw/ano=YYYY/mes=MM/dia=DD/
       │
  [ transform.py ]        ← Limpeza, padronização, métricas derivadas
       │
       ├──► S3 Processed  ← Parquet particionado (formato colunar)
       │    s3://bucket/processed/ano=YYYY/mes=MM/dia=DD/
       │
  [ load_rds.py ]         ← Carga incremental no Data Warehouse
       │
       ▼
  PostgreSQL / AWS RDS    ← Star Schema (fato + dimensões)
       │
       ▼
  Metabase Dashboard      ← Visualização interativa no navegador
```

---

## 📈 Ativos Monitorados

| Ticker | Empresa | Setor |
|--------|---------|-------|
| AAPL | Apple Inc. | Tecnologia |
| GOOGL | Alphabet (Google) | Tecnologia |
| MSFT | Microsoft Corp. | Tecnologia |
| AMZN | Amazon.com Inc. | Consumo |
| META | Meta Platforms (Facebook) | Tecnologia |

---

## 🧱 Modelagem Dimensional — Star Schema

```
         dim_tempo
        ┌──────────────┐
        │ id_tempo (PK)│
        │ data         │
        │ ano / mes    │
        │ trimestre    │
        │ dia_semana   │
        └──────┬───────┘
               │
               ▼
      ┌─────────────────────┐        dim_ativo
      │   fato_cotacoes     │◄──────┌──────────────┐
      │─────────────────────│       │ id_ativo (PK)│
      │ preco_abertura      │       │ simbolo      │
      │ preco_fechamento    │       │ nome_ativo   │
      │ preco_maximo        │       │ setor        │
      │ preco_minimo        │       └──────────────┘
      │ volume              │
      │ variacao_percentual │
      │ amplitude_diaria    │
      │ preco_medio         │
      └─────────────────────┘
```

**Granularidade:** 1 registro por ativo por dia.

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.11 |
| Extração | yfinance (Yahoo Finance API) |
| Transformação | Pandas, PyArrow |
| Data Lake | AWS S3 (JSON → Parquet) |
| Data Warehouse | PostgreSQL 16 / AWS RDS |
| Integração AWS | boto3 |
| Dashboard | Metabase |
| Containerização | Docker, Docker Compose |
| Modelagem | Star Schema (Kimball) |

---

## 📁 Estrutura do Projeto

```
finance-data-pipeline/
│
├── src/
│   ├── extract.py        # Extração de dados via Yahoo Finance
│   ├── upload_s3.py      # Upload para AWS S3 com boto3
│   ├── transform.py      # Limpeza, padronização e Parquet
│   ├── load_rds.py       # Carga incremental no PostgreSQL
│   └── run_pipeline.py   # Orquestrador principal
│
├── sql/
│   ├── create_tables.sql      # DDL — Star Schema completo
│   ├── indexes.sql            # Índices para performance
│   └── analytical_queries.sql # Queries com CTEs e Window Functions
│
├── docker-compose.yml    # PostgreSQL + Pipeline + Metabase
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Como Executar

### Pré-requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [Git](https://git-scm.com/downloads) instalado

### Passo a passo

**1. Clone o repositório**
```bash
git clone https://github.com/marinsonline-dev/finance-data-pipeline.git
cd finance-data-pipeline
```

**2. Configure as variáveis de ambiente**
```bash
cp .env.example .env
```

**3. Suba os serviços**
```bash
docker-compose up --build
```

**4. Acesse o dashboard**

Abra o navegador em: [http://localhost:3000](http://localhost:3000)

**5. Execute o pipeline manualmente**
```bash
# Dados de uma data específica
docker-compose run pipeline python src/run_pipeline.py --data 2026-05-14 --pular-s3

# Dados de hoje
docker-compose run pipeline python src/run_pipeline.py --pular-s3
```

---

## 📊 Consultas Analíticas

O projeto inclui queries avançadas demonstrando:

```sql
-- Média Móvel de 7 dias por ativo
AVG(preco_fechamento) OVER (
    PARTITION BY id_ativo
    ORDER BY data
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS media_movel_7d

-- Top 5 ativos por volume médio
SELECT simbolo, AVG(volume) AS volume_medio
FROM fato_cotacoes JOIN dim_ativo ...
GROUP BY simbolo
ORDER BY volume_medio DESC LIMIT 5;
```

Veja todas as queries em [`sql/analytical_queries.sql`](sql/analytical_queries.sql).

---

## 🧠 Conceitos Aplicados

| Conceito | Descrição |
|----------|-----------|
| **ETL** | Extract → Transform → Load completo |
| **Data Lake** | S3 com camadas Raw (JSON) e Processed (Parquet) |
| **Data Warehouse** | PostgreSQL com Star Schema |
| **Modelagem Dimensional** | Fato + Dimensões (metodologia Kimball) |
| **Carga Incremental** | ON CONFLICT DO NOTHING por data+ativo |
| **Window Functions** | Médias móveis, rankings, crescimento |
| **Cloud Computing** | AWS S3 e AWS RDS |
| **Containerização** | Docker + Docker Compose |
| **Boas Práticas** | Logging estruturado, tratamento de erros, modularidade |

---

## 👤 Autor

**Marcelo Marins** — Data Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/marcelo-marins-94925a369)
[![Portfolio](https://img.shields.io/badge/Portfolio-FF5722?style=for-the-badge&logo=google-chrome&logoColor=white)](https://marinsonline-dev.github.io/Portif-lio-Marcelo-Marins/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/marinsonline-dev)

---

> 💡 **Próximas melhorias planejadas:** Airflow para orquestração, Great Expectations para qualidade de dados, e deploy completo na AWS com Terraform.
