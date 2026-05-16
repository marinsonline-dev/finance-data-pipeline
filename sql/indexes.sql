-- =============================================================================
-- indexes.sql
-- Índices para otimização de queries analíticas
-- =============================================================================

-- ── fato_cotacoes ─────────────────────────────────────────────────────────────

-- Filtro por tempo (mais comum em análises temporais)
CREATE INDEX IF NOT EXISTS idx_fato_id_tempo
    ON fato_cotacoes (id_tempo);

-- Filtro por ativo
CREATE INDEX IF NOT EXISTS idx_fato_id_ativo
    ON fato_cotacoes (id_ativo);

-- Composite: ativo + tempo (padrão em janelas deslizantes)
CREATE INDEX IF NOT EXISTS idx_fato_ativo_tempo
    ON fato_cotacoes (id_ativo, id_tempo DESC);

-- Ordenação e filtro por variação (ranking de performance)
CREATE INDEX IF NOT EXISTS idx_fato_variacao
    ON fato_cotacoes (variacao_percentual DESC);

-- Ordenação por volume (top ativos mais negociados)
CREATE INDEX IF NOT EXISTS idx_fato_volume
    ON fato_cotacoes (volume DESC);

-- ── dim_tempo ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_tempo_ano_mes
    ON dim_tempo (ano, mes);

CREATE INDEX IF NOT EXISTS idx_tempo_data
    ON dim_tempo (data);

-- ── dim_ativo ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ativo_simbolo
    ON dim_ativo (simbolo);

CREATE INDEX IF NOT EXISTS idx_ativo_setor
    ON dim_ativo (setor);

-- =============================================================================
-- Verificar índices criados
-- =============================================================================
-- SELECT indexname, tablename, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
-- ORDER BY tablename, indexname;
