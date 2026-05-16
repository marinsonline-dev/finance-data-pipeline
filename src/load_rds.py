"""
load_rds.py
Carga incremental no Data Warehouse PostgreSQL (AWS RDS).
Implementa Star Schema: fato_cotacoes + dim_tempo + dim_ativo.
"""

import pandas as pd
import psycopg2
import logging
import os
from pathlib import Path
from datetime import datetime
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DIRETORIO_PROCESSED = Path("data/processed")


# ── Conexão ───────────────────────────────────────────────────────────────────

def conectar_rds():
    """Cria conexão com PostgreSQL/RDS via variáveis de ambiente."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("RDS_HOST", "localhost"),
            port=int(os.getenv("RDS_PORT", 5432)),
            user=os.getenv("RDS_USER", "postgres"),
            password=os.getenv("RDS_PASSWORD", "postgres"),
            dbname=os.getenv("RDS_DB", "finance_dw"),
        )
        conn.autocommit = False
        logger.info("Conexão RDS estabelecida.")
        return conn
    except Exception as e:
        logger.error(f"Falha ao conectar no RDS: {e}", exc_info=True)
        raise


# ── Dimensões ─────────────────────────────────────────────────────────────────

def upsert_dim_tempo(conn, datas: pd.Series) -> dict:
    """
    Insere datas na dim_tempo (se não existirem).
    Retorna dicionário {data: id_tempo}.
    """
    with conn.cursor() as cur:
        registros = []
        for data in datas.unique():
            dt = pd.Timestamp(data)
            registros.append((
                dt.date(),
                dt.year,
                dt.month,
                dt.day,
                dt.quarter,
                dt.day_of_week,  # 0=segunda, 6=domingo
                dt.strftime("%A"),
            ))

        sql = """
            INSERT INTO dim_tempo (data, ano, mes, dia, trimestre, dia_semana_num, dia_semana_nome)
            VALUES %s
            ON CONFLICT (data) DO NOTHING
            RETURNING id_tempo, data;
        """
        execute_values(cur, sql, registros)
        conn.commit()

        cur.execute("SELECT id_tempo, data FROM dim_tempo WHERE data = ANY(%s)",
                    ([r[0] for r in registros],))
        mapa = {str(row[1]): row[0] for row in cur.fetchall()}

    logger.info(f"dim_tempo: {len(mapa)} datas mapeadas.")
    return mapa


def upsert_dim_ativo(conn, simbolos: pd.Series) -> dict:
    """
    Insere ativos na dim_ativo (se não existirem).
    Retorna dicionário {simbolo: id_ativo}.
    """
    with conn.cursor() as cur:
        registros = [(s, s, None) for s in simbolos.unique()]  # (simbolo, nome, setor)

        sql = """
            INSERT INTO dim_ativo (simbolo, nome_ativo, setor)
            VALUES %s
            ON CONFLICT (simbolo) DO NOTHING
            RETURNING id_ativo, simbolo;
        """
        execute_values(cur, sql, registros)
        conn.commit()

        cur.execute("SELECT id_ativo, simbolo FROM dim_ativo WHERE simbolo = ANY(%s)",
                    ([r[0] for r in registros],))
        mapa = {row[1]: row[0] for row in cur.fetchall()}

    logger.info(f"dim_ativo: {len(mapa)} ativos mapeados.")
    return mapa


# ── Fato ──────────────────────────────────────────────────────────────────────

def carregar_fato_cotacoes(conn, df: pd.DataFrame, mapa_tempo: dict, mapa_ativo: dict):
    """
    Carga incremental em fato_cotacoes.
    Ignora registros já existentes (ON CONFLICT DO NOTHING).
    """
    registros = []
    for _, row in df.iterrows():
        chave_data = str(row["data"].date()) if hasattr(row["data"], "date") else str(row["data"])[:10]
        id_tempo = mapa_tempo.get(chave_data)
        id_ativo = mapa_ativo.get(row["simbolo"])

        if not id_tempo or not id_ativo:
            logger.warning(f"Chave não encontrada: data={chave_data}, ativo={row['simbolo']}")
            continue

        registros.append((
            id_tempo,
            id_ativo,
            float(row.get("preco_abertura", 0) or 0),
            float(row.get("preco_fechamento", 0) or 0),
            float(row.get("preco_maximo", 0) or 0),
            float(row.get("preco_minimo", 0) or 0),
            int(row.get("volume", 0) or 0),
            float(row.get("variacao_percentual", 0) or 0),
            float(row.get("amplitude_diaria", 0) or 0),
            float(row.get("preco_medio", 0) or 0),
        ))

    with conn.cursor() as cur:
        sql = """
            INSERT INTO fato_cotacoes (
                id_tempo, id_ativo,
                preco_abertura, preco_fechamento, preco_maximo, preco_minimo,
                volume, variacao_percentual, amplitude_diaria, preco_medio
            ) VALUES %s
            ON CONFLICT (id_tempo, id_ativo) DO NOTHING;
        """
        execute_values(cur, sql, registros)
        conn.commit()

    logger.info(f"fato_cotacoes: {len(registros)} registros inseridos.")


# ── Orquestrador ──────────────────────────────────────────────────────────────

def carregar_parquet_processed(data_referencia=None) -> pd.DataFrame:
    """Carrega Parquet da camada Processed para a data informada."""
    data_ref = data_referencia or datetime.today().strftime("%Y-%m-%d")
    ano, mes, dia = data_ref.split("-")
    caminho = DIRETORIO_PROCESSED / f"ano={ano}" / f"mes={mes}" / f"dia={dia}" / "cotacoes.parquet"

    if not caminho.exists():
        logger.error(f"Parquet não encontrado: {caminho}")
        return pd.DataFrame()

    df = pd.read_parquet(caminho)
    logger.info(f"Parquet carregado: {caminho} | {len(df)} registros")
    return df


def executar_carga(data_referencia=None):
    """Pipeline completo de carga no Data Warehouse."""
    logger.info("=== INÍCIO DA CARGA NO DATA WAREHOUSE ===")

    df = carregar_parquet_processed(data_referencia)
    if df.empty:
        logger.error("Sem dados para carregar. Abortando.")
        return

    conn = conectar_rds()
    try:
        mapa_tempo = upsert_dim_tempo(conn, df["data"])
        mapa_ativo = upsert_dim_ativo(conn, df["simbolo"])
        carregar_fato_cotacoes(conn, df, mapa_tempo, mapa_ativo)
        logger.info("=== CARGA CONCLUÍDA COM SUCESSO ===")
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na carga. Rollback executado: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    executar_carga()
