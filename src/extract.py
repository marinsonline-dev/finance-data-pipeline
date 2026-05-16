"""
extract.py
Extração de dados financeiros via yfinance (Yahoo Finance).
Suporte a múltiplos ativos com atualização incremental diária.
"""

import yfinance as yf
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ATIVOS_PADRAO = ["AAPL", "GOOGL", "MSFT", "AMZN", "META"]
DIRETORIO_RAW = Path("data/raw")


def extrair_cotacoes(simbolos=None, data_inicio=None, data_fim=None):
    """
    Extrai cotações históricas para uma lista de símbolos.

    Args:
        simbolos: Lista de tickers (ex: ["AAPL", "MSFT"])
        data_inicio: Data inicial YYYY-MM-DD (padrão: ontem)
        data_fim: Data final YYYY-MM-DD (padrão: hoje)

    Returns:
        Dicionário {simbolo: DataFrame com cotações brutas}
    """
    if simbolos is None:
        simbolos = ATIVOS_PADRAO

    hoje = datetime.today()
    data_fim = data_fim or hoje.strftime("%Y-%m-%d")
    data_inicio = data_inicio or (hoje - timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(f"Extração | Ativos: {simbolos} | Período: {data_inicio} → {data_fim}")

    resultados = {}

    for simbolo in simbolos:
        try:
            logger.info(f"Baixando {simbolo}...")
            ticker = yf.Ticker(simbolo)
            df = ticker.history(start=data_inicio, end=data_fim)

            if df.empty:
                logger.warning(f"Sem dados para {simbolo} no período.")
                continue

            df = df.reset_index()
            df["simbolo"] = simbolo
            df["extraido_em"] = datetime.utcnow().isoformat()

            resultados[simbolo] = df
            logger.info(f"{simbolo}: {len(df)} registros extraídos.")

        except Exception as e:
            logger.error(f"Erro ao extrair {simbolo}: {e}", exc_info=True)

    logger.info(f"Concluído | {len(resultados)}/{len(simbolos)} ativos com sucesso.")
    return resultados


def salvar_raw_local(dados, data_referencia=None):
    """
    Salva dados brutos em JSON particionado por data (espelha estrutura S3).
    Estrutura: data/raw/ano=YYYY/mes=MM/dia=DD/<SIMBOLO>.json
    """
    data_ref = data_referencia or datetime.today().strftime("%Y-%m-%d")
    ano, mes, dia = data_ref.split("-")
    caminhos = []

    for simbolo, df in dados.items():
        diretorio = DIRETORIO_RAW / f"ano={ano}" / f"mes={mes}" / f"dia={dia}"
        diretorio.mkdir(parents=True, exist_ok=True)

        caminho = diretorio / f"{simbolo}.json"
        registros = df.to_dict(orient="records")

        # Serializa datetime para string
        for r in registros:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)

        logger.info(f"Salvo: {caminho}")
        caminhos.append(caminho)

    return caminhos


if __name__ == "__main__":
    dados = extrair_cotacoes()
    salvar_raw_local(dados)
