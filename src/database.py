import pymssql
from contextlib import contextmanager
from typing import Any, Dict, Optional
import logging
from datetime import datetime
from .config import db_config


class DatabaseManager:
    def __init__(self):
        self._pool = {}
        self._max_connections = 5
        self._host = db_config.host
        self._user = db_config.user
        self._password = db_config.password

    def buscar_ordem(self, id_ordem: int) -> Optional[Dict[str, Any]]:
        """Busca uma ordem de produção pelo ID"""
        try:
            with pymssql.connect(db_config.host, db_config.user, db_config.password, "SIP") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        Id,
                        Artigo,
                        DescricaoArtigo,
                        CadenciaArtigo,
                        QuantidadeTotal,
                        NumeroOrdem
                    FROM krones_historico_contagens
                    WHERE Ordem = %s
                """,
                    (id_ordem,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "Id": row[0],
                        "Artigo": row[1],
                        "DescricaoArtigo": row[2],
                        "CadenciaArtigo": row[3],
                        "QuantidadeTotal": row[4],
                        "NumeroOrdem": row[5],
                    }
                return None
        except Exception as e:
            logging.error(f"Erro ao buscar ordem {id_ordem}: {e}")
            raise

    def buscar_ordem_producao(self, ordem: str) -> Optional[Dict[str, Any]]:
        """Busca os dados de uma ordem de produção"""
        try:
            with pymssql.connect(self._host, "Leitura", "Leitura", "VGDadosPocas") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        Id,
                        ArtigoGCP as Artigo,
                        DescricaoGCP as DescricaoArtigo,
                        ISNULL(CDU_Cadencia, 6000) as CadenciaArtigo
                    FROM
                        prd_ORDEM_PRODUCAO op
                    INNER JOIN
                        PRIPOCAS.dbo.Artigo art
                    ON
                        op.ArtigoGCP = art.Artigo
                    WHERE 
                        nEMPRESA = 1 AND
                        NORDEM = REPLACE(%s, '-', '/')
                    """,
                    (ordem,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "Id": row[0],
                        "Artigo": row[1],
                        "DescricaoArtigo": row[2],
                        "CadenciaArtigo": row[3],
                    }
                return None
        except Exception as e:
            logging.error(f"Erro ao buscar ordem de produção: {e}")
            raise

    def gravar_contagem(self, contador, id_ordem: int, contagem: int, contagem_total: int):
        """Grava uma contagem parcial no banco SIP e no histórico"""
        try:
            with pymssql.connect(self._host, self._user, self._password, "SIP") as conn:
                cursor = conn.cursor()
                
                # Primeira query - Grava na tabela de contagem atual
                cursor.execute(
                    """
                    INSERT INTO krones_contadoreslinhacontagem
                        (IdContagem, ContagemAtual, Objetivo, DataLeitura)
                    VALUES
                        (%s, %s, %s, %s)
                    """,
                    (id_ordem, contagem, contagem_total, datetime.now()),
                )

                # Segunda query - Grava no histórico
                data_atual = datetime.now()
                
                SQL = """
                    INSERT INTO krones_historico_contagens
                        (DataDados, Ordem, Artigo, DescricaoArtigo, CadenciaArtigo, Inicio, Fim, ContagemAtual, ContagemTotal, MediaProducao, EstimativaFecho, Paragens, Quebras, EstadoPorta, EstadoContador, EstadoConfiguracao, Nominal, Media, Cadencia, Tempo)
                    VALUES
                        (%(DataDados)s, %(Ordem)s, %(Artigo)s, %(DescricaoArtigo)s, %(CadenciaArtigo)s, %(Inicio)s, %(Fim)s, %(ContagemAtual)s, %(ContagemTotal)s, %(MediaProducao)s, %(EstimativaFecho)s, %(Paragens)s, %(Quebras)s, %(EstadoPorta)s, %(EstadoContador)s, %(EstadoConfiguracao)s, %(Nominal)s, %(Media)s, %(Cadencia)s, %(Tempo)s)
                """
                params = {
                    "DataDados": data_atual,
                    "Ordem": id_ordem,
                    "Artigo": contador.state.artigo,
                    "DescricaoArtigo": contador.state.descricao_artigo,
                    "CadenciaArtigo": contador.state.cadencia_artigo,
                    "Inicio": contador.state.tempo_inicio,
                    "Fim": contador.state.tempo_fim,
                    "ContagemAtual": contador.state.contagem_atual,
                    "ContagemTotal": contador.state.contagem_total,
                    "MediaProducao": contador.state.estatistica_media[-1] if contador.state.estatistica_media else None,
                    "EstimativaFecho": None,  # Será calculado separadamente se necessário
                    "Paragens": contador.state.paragens[-1] if contador.state.paragens else None,
                    "Quebras": contador.state.quebras,
                    "EstadoPorta": contador.state.porta_estado,
                    "EstadoContador": contador.state.estado,
                    "EstadoConfiguracao": contador.state.configurado,
                    "Nominal": contador.state.estatistica_gfa[-1] if contador.state.estatistica_gfa else None,
                    "Media": contador.state.estatistica_media[-1] if contador.state.estatistica_media else None,
                    "Cadencia": contador.state.estatistica_cadencia[-1] if contador.state.estatistica_cadencia else None,
                    "Tempo": contador.state.estatistica_tempo[-1] if contador.state.estatistica_tempo else None,
                }

                cursor.execute(SQL, params)
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Erro ao gravar contagem: {e}")
            raise

    def gravar_estatisticas(self, id_ordem: int, stats: Dict[str, Any]):
        """Grava as estatísticas finais no banco SIP"""
        try:
            with pymssql.connect(self._host, self._user, self._password, "SIP") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE krones_contadoreslinha
                    SET
                        Ativo = 0,
                        QuantidadeFinal = %s,
                        Quebras = %s,
                        MediaProducao = %s,
                        Abertura = %s,
                        Fecho = %s
                    WHERE
                        Ativo = 1 AND
                        Ordem = %s
                    """,
                    (
                        stats["contagem_final"],
                        stats["quebras"],
                        stats["media_producao"],
                        stats["tempo_inicio"],
                        stats["tempo_fim"],
                        id_ordem,
                    ),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Erro ao gravar estatísticas: {e}")
            raise

    def desativar_ordens_ativas(self):
        """Desativa todas as ordens de produção ativas"""
        try:
            with pymssql.connect(self._host, self._user, self._password, "SIP") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE krones_contadoreslinha
                    SET Ativo = 0
                    WHERE Ativo = 1
                    """
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Erro ao desativar ordens ativas: {e}")
            raise
