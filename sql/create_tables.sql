-- =============================================================================
-- create_tables.sql
-- Data Warehouse Financeiro — Star Schema
-- Granularidade: 1 linha por ativo por dia em fato_cotacoes
-- =============================================================================

-- Extensão para UUIDs (opcional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- DIMENSÃO TEMPO
-- =============================================================================
CREATE TABLE IF NOT EXISTS dim_tempo (
    id_tempo          SERIAL PRIMARY KEY,
    data              DATE        NOT NULL UNIQUE,
    ano               SMALLINT    NOT NULL,
    mes               SMALLINT    NOT NULL,
    dia               SMALLINT    NOT NULL,
    trimestre         SMALLINT    NOT NULL,
    dia_semana_num    SMALLINT    NOT NULL,  -- 0=segunda ... 6=domingo
    dia_semana_nome   VARCHAR(15) NOT NULL,
    eh_fim_de_semana  BOOLEAN     GENERATED ALWAYS AS (dia_semana_num >= 5) STORED,
    criado_em         TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dim_tempo IS 'Dimensão temporal com granularidade diária.';
COMMENT ON COLUMN dim_tempo.dia_semana_num IS '0=segunda-feira, 6=domingo (padrão Python/pandas).';


-- =============================================================================
-- DIMENSÃO ATIVO
-- =============================================================================
CREATE TABLE IF NOT EXISTS dim_ativo (
    id_ativo    SERIAL PRIMARY KEY,
    simbolo     VARCHAR(20)  NOT NULL UNIQUE,
    nome_ativo  VARCHAR(200),
    setor       VARCHAR(100),
    pais        VARCHAR(50)  DEFAULT 'US',
    moeda       VARCHAR(10)  DEFAULT 'USD',
    ativo       BOOLEAN      DEFAULT TRUE,
    criado_em   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP  DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dim_ativo IS 'Dimensão de ativos financeiros (ações, ETFs, etc).';


-- =============================================================================
-- TABELA FATO: COTAÇÕES
-- Granularidade: 1 linha por ativo por dia
-- =============================================================================
CREATE TABLE IF NOT EXISTS fato_cotacoes (
    id_cotacao          BIGSERIAL   PRIMARY KEY,
    id_tempo            INTEGER     NOT NULL REFERENCES dim_tempo(id_tempo),
    id_ativo            INTEGER     NOT NULL REFERENCES dim_ativo(id_ativo),

    -- Medidas de preço
    preco_abertura      NUMERIC(12, 4) NOT NULL,
    preco_fechamento    NUMERIC(12, 4) NOT NULL,
    preco_maximo        NUMERIC(12, 4) NOT NULL,
    preco_minimo        NUMERIC(12, 4) NOT NULL,

    -- Volume
    volume              BIGINT         NOT NULL DEFAULT 0,

    -- Métricas derivadas
    variacao_percentual NUMERIC(8, 4),   -- (fechamento - abertura) / abertura * 100
    amplitude_diaria    NUMERIC(12, 4),  -- maximo - minimo
    preco_medio         NUMERIC(12, 4),  -- (abertura + fechamento) / 2

    -- Metadados
    carregado_em        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Chave natural: um registro por ativo por dia
    CONSTRAINT uq_cotacao_ativo_dia UNIQUE (id_tempo, id_ativo)
);

COMMENT ON TABLE fato_cotacoes IS 'Fato com cotações diárias de ativos financeiros.';
COMMENT ON COLUMN fato_cotacoes.variacao_percentual IS 'Variação % entre abertura e fechamento do dia.';
COMMENT ON COLUMN fato_cotacoes.amplitude_diaria IS 'Diferença entre preço máximo e mínimo do dia.';
