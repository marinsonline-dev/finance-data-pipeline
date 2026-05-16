-- =============================================================================
-- analytical_queries.sql
-- Consultas analíticas avançadas — Data Warehouse Financeiro
-- Técnicas: CTE, Window Functions, Agregações, EXPLAIN
-- =============================================================================


-- =============================================================================
-- 1. MÉDIA MÓVEL DE 7 E 30 DIAS (Window Function)
-- Identifica tendências de preço por ativo
-- =============================================================================
WITH cotacoes_ordenadas AS (
    SELECT
        t.data,
        a.simbolo,
        f.preco_fechamento,
        AVG(f.preco_fechamento) OVER (
            PARTITION BY f.id_ativo
            ORDER BY t.data
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS media_movel_7d,
        AVG(f.preco_fechamento) OVER (
            PARTITION BY f.id_ativo
            ORDER BY t.data
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS media_movel_30d
    FROM fato_cotacoes f
    JOIN dim_tempo  t ON t.id_tempo = f.id_tempo
    JOIN dim_ativo  a ON a.id_ativo = f.id_ativo
)
SELECT
    data,
    simbolo,
    ROUND(preco_fechamento::NUMERIC, 2)  AS fechamento,
    ROUND(media_movel_7d::NUMERIC, 2)    AS mm_7d,
    ROUND(media_movel_30d::NUMERIC, 2)   AS mm_30d
FROM cotacoes_ordenadas
ORDER BY simbolo, data DESC
LIMIT 100;


-- =============================================================================
-- 2. CRESCIMENTO PERCENTUAL ACUMULADO NO MÊS (Window Function)
-- Compara fechamento atual com o primeiro dia do mês
-- =============================================================================
WITH primeiro_do_mes AS (
    SELECT
        f.id_ativo,
        t.ano,
        t.mes,
        FIRST_VALUE(f.preco_fechamento) OVER (
            PARTITION BY f.id_ativo, t.ano, t.mes
            ORDER BY t.data
        ) AS preco_inicio_mes
    FROM fato_cotacoes f
    JOIN dim_tempo t ON t.id_tempo = f.id_tempo
)
SELECT
    t.data,
    a.simbolo,
    f.preco_fechamento,
    pm.preco_inicio_mes,
    ROUND(
        ((f.preco_fechamento - pm.preco_inicio_mes) / pm.preco_inicio_mes * 100)::NUMERIC, 2
    ) AS crescimento_mensal_pct
FROM fato_cotacoes f
JOIN dim_tempo  t  ON t.id_tempo  = f.id_tempo
JOIN dim_ativo  a  ON a.id_ativo  = f.id_ativo
JOIN primeiro_do_mes pm
    ON pm.id_ativo = f.id_ativo
    AND pm.ano     = t.ano
    AND pm.mes     = t.mes
ORDER BY a.simbolo, t.data DESC;


-- =============================================================================
-- 3. TOP 5 ATIVOS COM MAIOR VOLUME MÉDIO (Agregação)
-- =============================================================================
SELECT
    a.simbolo,
    a.nome_ativo,
    COUNT(*)                                  AS dias_negociados,
    ROUND(AVG(f.volume)::NUMERIC, 0)          AS volume_medio_diario,
    MAX(f.volume)                              AS volume_maximo,
    SUM(f.volume)                              AS volume_total
FROM fato_cotacoes f
JOIN dim_ativo a ON a.id_ativo = f.id_ativo
GROUP BY a.simbolo, a.nome_ativo
ORDER BY volume_medio_diario DESC
LIMIT 5;


-- =============================================================================
-- 4. AGREGAÇÃO MENSAL — Resumo de performance por ativo e mês
-- =============================================================================
SELECT
    t.ano,
    t.mes,
    a.simbolo,
    ROUND(MIN(f.preco_minimo)::NUMERIC, 2)           AS minimo_mensal,
    ROUND(MAX(f.preco_maximo)::NUMERIC, 2)           AS maximo_mensal,
    ROUND(AVG(f.preco_fechamento)::NUMERIC, 2)       AS fechamento_medio,
    ROUND(SUM(f.volume::NUMERIC) / 1e6, 2)           AS volume_total_milhoes,
    ROUND(AVG(f.variacao_percentual)::NUMERIC, 4)    AS variacao_media_diaria_pct,
    COUNT(*)                                          AS dias_com_dados
FROM fato_cotacoes f
JOIN dim_tempo t ON t.id_tempo = f.id_tempo
JOIN dim_ativo a ON a.id_ativo = f.id_ativo
GROUP BY t.ano, t.mes, a.simbolo
ORDER BY t.ano DESC, t.mes DESC, a.simbolo;


-- =============================================================================
-- 5. RANKING DE PERFORMANCE — Melhores ativos por variação percentual acumulada
-- Usa ROW_NUMBER para ranking dentro de cada mês
-- =============================================================================
WITH performance_mensal AS (
    SELECT
        t.ano,
        t.mes,
        a.simbolo,
        ROUND(SUM(f.variacao_percentual)::NUMERIC, 4) AS variacao_acumulada_pct,
        COUNT(*) AS dias
    FROM fato_cotacoes f
    JOIN dim_tempo t ON t.id_tempo = f.id_tempo
    JOIN dim_ativo a ON a.id_ativo = f.id_ativo
    GROUP BY t.ano, t.mes, a.simbolo
),
ranking AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY ano, mes
            ORDER BY variacao_acumulada_pct DESC
        ) AS rank_performance
    FROM performance_mensal
)
SELECT
    ano,
    mes,
    rank_performance AS ranking,
    simbolo,
    variacao_acumulada_pct,
    dias
FROM ranking
WHERE rank_performance <= 5
ORDER BY ano DESC, mes DESC, rank_performance;


-- =============================================================================
-- 6. VOLATILIDADE DIÁRIA — Desvio padrão do fechamento (Window 30 dias)
-- =============================================================================
SELECT
    t.data,
    a.simbolo,
    f.preco_fechamento,
    ROUND(
        STDDEV(f.preco_fechamento) OVER (
            PARTITION BY f.id_ativo
            ORDER BY t.data
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        )::NUMERIC, 4
    ) AS volatilidade_30d
FROM fato_cotacoes f
JOIN dim_tempo t ON t.id_tempo = f.id_tempo
JOIN dim_ativo a ON a.id_ativo = f.id_ativo
ORDER BY a.simbolo, t.data DESC;


-- =============================================================================
-- 7. ANÁLISE DE PERFORMANCE — EXPLAIN para otimização
-- =============================================================================
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    a.simbolo,
    t.data,
    f.preco_fechamento,
    f.variacao_percentual
FROM fato_cotacoes f
JOIN dim_tempo t ON t.id_tempo = f.id_tempo
JOIN dim_ativo a ON a.id_ativo = f.id_ativo
WHERE t.ano = 2025
  AND t.mes = 5
ORDER BY a.simbolo, t.data;
