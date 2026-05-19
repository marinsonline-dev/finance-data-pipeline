"""
extract.py
Extração de dados financeiros via yfinance (Yahoo Finance).
Usa yf.download para maior compatibilidade e confiabilidade.
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
    Usa yf.download para maior compatibilidade.
    """
    if simbolos is None:
        simbolos = ATIVOS_PADRAO

    hoje = datetime.today()
    # Adiciona 1 dia ao fim para incluir a data final
    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1) if data_fim else hoje + timedelta(days=1)
    data_fim_str = data_fim_dt.strftime("%Y-%m-%d")
    data_inicio = data_inicio or (hoje - timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(f"Extração | Ativos: {simbolos} | Período: {data_inicio} → {data_fim or hoje.strftime('%Y-%m-%d')}")

    resultados = {}

    for simbolo in simbolos:
        try:
            logger.info(f"Baixando {simbolo}...")
            df = yf.download(simbolo, start=data_inicio, end=data_fim_str, progress=False)

            if df.empty:
                logger.warning(f"Sem dados para {simbolo} no período.")
                continue

            # Flatten colunas multi-level se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()
            df.columns = [str(c) for c in df.columns]
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
    Salva dados brutos em JSON particionado por data.
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
