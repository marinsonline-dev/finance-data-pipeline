"""
transform.py
Transformação dos dados brutos (Raw) para camada Processed.
Limpeza, padronização, métricas derivadas e exportação em Parquet.
"""

import pandas as pd
import logging
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DIRETORIO_RAW = Path("data/raw")
DIRETORIO_PROCESSED = Path("data/processed")


def carregar_json_raw(data_referencia=None) -> pd.DataFrame:
    """
    Lê todos os JSONs da camada Raw para a data informada.

    Args:
        data_referencia: Formato YYYY-MM-DD (padrão: hoje)

    Returns:
        DataFrame consolidado com todos os ativos do dia
    """
    data_ref = data_referencia or datetime.today().strftime("%Y-%m-%d")
    ano, mes, dia = data_ref.split("-")

    diretorio = DIRETORIO_RAW / f"ano={ano}" / f"mes={mes}" / f"dia={dia}"

    if not diretorio.exists():
        logger.error(f"Diretório não encontrado: {diretorio}")
        return pd.DataFrame()

    frames = []
    for arquivo in diretorio.glob("*.json"):
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
        df = pd.DataFrame(dados)
        frames.append(df)
        logger.info(f"Carregado: {arquivo.name} | {len(df)} registros")

    if not frames:
        logger.warning("Nenhum arquivo JSON encontrado.")
        return pd.DataFrame()

    df_total = pd.concat(frames, ignore_index=True)
    logger.info(f"Total carregado: {len(df_total)} registros.")
    return df_total


def transformar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica todas as transformações na camada Raw:
    - Padronização de colunas
    - Conversão de tipos
    - Tratamento de nulos
    - Criação de métricas derivadas
    """
    if df.empty:
        logger.warning("DataFrame vazio. Nada a transformar.")
        return df

    logger.info("Iniciando transformações...")

    # ── Renomear colunas ──────────────────────────────────────────────────────
    mapa_colunas = {
        "Date": "data",
        "Open": "preco_abertura",
        "High": "preco_maximo",
        "Low": "preco_minimo",
        "Close": "preco_fechamento",
        "Volume": "volume",
        "simbolo": "simbolo",
        "extraido_em": "extraido_em",
    }
    df = df.rename(columns={k: v for k, v in mapa_colunas.items() if k in df.columns})

    # ── Manter apenas colunas necessárias ─────────────────────────────────────
    colunas_alvo = [
        "data", "simbolo", "preco_abertura", "preco_fechamento",
        "preco_maximo", "preco_minimo", "volume", "extraido_em",
    ]
    df = df[[c for c in colunas_alvo if c in df.columns]]

    # ── Tipos ─────────────────────────────────────────────────────────────────
    df["data"] = pd.to_datetime(df["data"], utc=True).dt.tz_localize(None)
    df["data"] = df["data"].dt.normalize()

    for col in ["preco_abertura", "preco_fechamento", "preco_maximo", "preco_minimo"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(4)

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

    # ── Nulos ─────────────────────────────────────────────────────────────────
    nulos_antes = df.isnull().sum().sum()
    df = df.dropna(subset=["preco_fechamento", "simbolo", "data"])
    nulos_depois = df.isnull().sum().sum()
    logger.info(f"Nulos removidos: {nulos_antes - nulos_depois}")

    # ── Deduplicação ──────────────────────────────────────────────────────────
    df = df.drop_duplicates(subset=["data", "simbolo"])

    # ── Métricas derivadas ────────────────────────────────────────────────────
    df = df.sort_values(["simbolo", "data"])

    # Variação percentual diária: (fechamento - abertura) / abertura * 100
    df["variacao_percentual"] = (
        (df["preco_fechamento"] - df["preco_abertura"]) / df["preco_abertura"] * 100
    ).round(4)

    # Amplitude diária: máximo - mínimo
    df["amplitude_diaria"] = (df["preco_maximo"] - df["preco_minimo"]).round(4)

    # Média entre abertura e fechamento
    df["preco_medio"] = (
        (df["preco_abertura"] + df["preco_fechamento"]) / 2
    ).round(4)

    # Ano, mês, dia para particionamento
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["dia"] = df["data"].dt.day

    logger.info(f"Transformação concluída | {len(df)} registros processados.")
    return df


def salvar_processed(df: pd.DataFrame, data_referencia=None) -> Path:
    """
    Salva DataFrame transformado em formato Parquet particionado.
    Estrutura: data/processed/ano=YYYY/mes=MM/dia=DD/cotacoes.parquet
    """
    if df.empty:
        logger.warning("DataFrame vazio. Nada a salvar.")
        return None

    data_ref = data_referencia or datetime.today().strftime("%Y-%m-%d")
    ano, mes, dia = data_ref.split("-")

    diretorio = DIRETORIO_PROCESSED / f"ano={ano}" / f"mes={mes}" / f"dia={dia}"
    diretorio.mkdir(parents=True, exist_ok=True)

    caminho = diretorio / "cotacoes.parquet"
    df.to_parquet(caminho, index=False, engine="pyarrow")

    logger.info(f"Parquet salvo: {caminho} | {len(df)} registros")
    return caminho


if __name__ == "__main__":
    df_raw = carregar_json_raw()
    df_proc = transformar(df_raw)
    salvar_processed(df_proc)
