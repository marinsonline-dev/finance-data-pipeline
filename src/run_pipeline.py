"""
run_pipeline.py
Orquestrador principal do pipeline financeiro.
Executa as etapas: Extract → Upload S3 → Transform → Load RDS

Uso:
    python src/run_pipeline.py
    python src/run_pipeline.py --data 2025-05-14
    python src/run_pipeline.py --ativos AAPL MSFT GOOGL --data 2025-05-14
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Adiciona src ao path para imports relativos
sys.path.insert(0, os.path.dirname(__file__))

from extract import extrair_cotacoes, salvar_raw_local
from upload_s3 import fazer_upload
from transform import carregar_json_raw, transformar, salvar_processed
from load_rds import executar_carga

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ATIVOS_PADRAO = ["AAPL", "GOOGL", "MSFT", "AMZN", "META"]


def parsear_argumentos():
    parser = argparse.ArgumentParser(description="Pipeline de Dados Financeiros")
    parser.add_argument(
        "--data",
        type=str,
        default=datetime.today().strftime("%Y-%m-%d"),
        help="Data de referência no formato YYYY-MM-DD (padrão: hoje)",
    )
    parser.add_argument(
        "--ativos",
        nargs="+",
        default=ATIVOS_PADRAO,
        help="Lista de tickers (ex: AAPL MSFT GOOGL)",
    )
    parser.add_argument(
        "--pular-s3",
        action="store_true",
        help="Pula o upload para S3 (útil para testes locais)",
    )
    parser.add_argument(
        "--pular-rds",
        action="store_true",
        help="Pula a carga no RDS (útil para testes locais)",
    )
    return parser.parse_args()


def executar_pipeline(data_ref: str, ativos: list, pular_s3=False, pular_rds=False):
    inicio = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"PIPELINE INICIADO | Data: {data_ref} | Ativos: {ativos}")
    logger.info("=" * 60)

    erros = []

    # ── ETAPA 1: Extração ────────────────────────────────────────────────────
    try:
        logger.info(">>> ETAPA 1/4: Extração de dados (Yahoo Finance)")
        dados_raw = extrair_cotacoes(simbolos=ativos, data_inicio=data_ref, data_fim=data_ref)
        caminhos_raw = salvar_raw_local(dados_raw, data_referencia=data_ref)
        logger.info(f"Extração OK | {len(caminhos_raw)} arquivos gerados.")
    except Exception as e:
        logger.error(f"FALHA na Extração: {e}", exc_info=True)
        erros.append("extract")
        return resumo_pipeline(inicio, erros)

    # ── ETAPA 2: Upload S3 ───────────────────────────────────────────────────
    if not pular_s3:
        try:
            logger.info(">>> ETAPA 2/4: Upload para S3 (camada Raw)")
            enviados = fazer_upload(caminhos_raw, camada="raw")
            logger.info(f"Upload S3 OK | {len(enviados)} arquivos enviados.")
        except Exception as e:
            logger.error(f"FALHA no Upload S3: {e}", exc_info=True)
            erros.append("upload_s3")
    else:
        logger.info(">>> ETAPA 2/4: Upload S3 pulado (--pular-s3).")

    # ── ETAPA 3: Transformação ───────────────────────────────────────────────
    try:
        logger.info(">>> ETAPA 3/4: Transformação (Raw → Processed)")
        df_raw = carregar_json_raw(data_referencia=data_ref)
        df_proc = transformar(df_raw)
        caminho_parquet = salvar_processed(df_proc, data_referencia=data_ref)
        logger.info(f"Transformação OK | Parquet: {caminho_parquet}")

        # Upload do Parquet para S3 (camada processed)
        if not pular_s3 and caminho_parquet:
            fazer_upload([caminho_parquet], camada="processed")
    except Exception as e:
        logger.error(f"FALHA na Transformação: {e}", exc_info=True)
        erros.append("transform")
        return resumo_pipeline(inicio, erros)

    # ── ETAPA 4: Carga RDS ───────────────────────────────────────────────────
    if not pular_rds:
        try:
            logger.info(">>> ETAPA 4/4: Carga no Data Warehouse (PostgreSQL/RDS)")
            executar_carga(data_referencia=data_ref)
            logger.info("Carga RDS OK.")
        except Exception as e:
            logger.error(f"FALHA na Carga RDS: {e}", exc_info=True)
            erros.append("load_rds")
    else:
        logger.info(">>> ETAPA 4/4: Carga RDS pulada (--pular-rds).")

    return resumo_pipeline(inicio, erros)


def resumo_pipeline(inicio: datetime, erros: list):
    duracao = (datetime.utcnow() - inicio).total_seconds()
    status = "SUCESSO" if not erros else f"FALHA em: {', '.join(erros)}"
    logger.info("=" * 60)
    logger.info(f"PIPELINE CONCLUÍDO | Status: {status} | Duração: {duracao:.1f}s")
    logger.info("=" * 60)
    return len(erros) == 0


if __name__ == "__main__":
    args = parsear_argumentos()
    sucesso = executar_pipeline(
        data_ref=args.data,
        ativos=args.ativos,
        pular_s3=args.pular_s3,
        pular_rds=args.pular_rds,
    )
    sys.exit(0 if sucesso else 1)
