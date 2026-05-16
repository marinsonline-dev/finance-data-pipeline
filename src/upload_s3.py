"""
upload_s3.py
Upload de arquivos para AWS S3 com suporte a particionamento por data.
Utiliza boto3 com autenticação via variáveis de ambiente.
"""

import boto3
import logging
import os
from pathlib import Path
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "data-lake-finance")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def criar_cliente_s3():
    """Cria e retorna cliente S3 autenticado via variáveis de ambiente."""
    try:
        client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        logger.info("Cliente S3 criado com sucesso.")
        return client
    except NoCredentialsError:
        logger.error("Credenciais AWS não encontradas. Verifique o .env.")
        raise


def montar_chave_s3(caminho_local: Path, camada: str = "raw") -> str:
    """
    Converte caminho local para chave S3 particionada.

    Exemplo:
        data/raw/ano=2025/mes=05/dia=14/AAPL.json
        → s3://bucket/raw/ano=2025/mes=05/dia=14/AAPL.json
    """
    partes = caminho_local.parts
    idx = next((i for i, p in enumerate(partes) if p == camada), None)
    if idx is not None:
        return "/".join(partes[idx:])
    return f"{camada}/{caminho_local.name}"


def fazer_upload(caminhos: list, camada: str = "raw", bucket: str = S3_BUCKET) -> list:
    """
    Realiza upload de uma lista de arquivos locais para o S3.

    Args:
        caminhos: Lista de Path com arquivos a enviar
        camada: Camada do Data Lake (raw, processed, curated)
        bucket: Nome do bucket S3

    Returns:
        Lista de chaves S3 enviadas com sucesso
    """
    client = criar_cliente_s3()
    enviados = []

    for caminho in caminhos:
        caminho = Path(caminho)
        if not caminho.exists():
            logger.warning(f"Arquivo não encontrado: {caminho}")
            continue

        chave = montar_chave_s3(caminho, camada)

        try:
            client.upload_file(str(caminho), bucket, chave)
            uri = f"s3://{bucket}/{chave}"
            logger.info(f"Upload OK: {uri}")
            enviados.append(chave)

        except ClientError as e:
            logger.error(f"Falha no upload de {caminho}: {e}", exc_info=True)

    logger.info(f"Upload concluído | {len(enviados)}/{len(caminhos)} arquivos enviados.")
    return enviados


def listar_arquivos_s3(prefixo: str, bucket: str = S3_BUCKET) -> list:
    """Lista arquivos no S3 com determinado prefixo."""
    client = criar_cliente_s3()
    try:
        paginator = client.get_paginator("list_objects_v2")
        chaves = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefixo):
            for obj in page.get("Contents", []):
                chaves.append(obj["Key"])
        logger.info(f"{len(chaves)} arquivos encontrados em s3://{bucket}/{prefixo}")
        return chaves
    except ClientError as e:
        logger.error(f"Erro ao listar S3: {e}", exc_info=True)
        return []


if __name__ == "__main__":
    # Teste local — lista arquivos raw do dia
    hoje = datetime.today()
    prefixo = f"raw/ano={hoje.year}/mes={hoje.month:02d}/dia={hoje.day:02d}/"
    listar_arquivos_s3(prefixo)
