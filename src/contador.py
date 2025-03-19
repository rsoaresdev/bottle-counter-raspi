from dataclasses import dataclass, field
from datetime import datetime, time as datetime_time
from typing import List, Optional, Dict, Any
import threading
import logging
import numpy as np
from .gpio_handler import GPIOHandler
from .database import DatabaseManager
import time
import pymssql

@dataclass
class ContadorState:
    """Classe para gerenciar o estado do contador"""

    artigo: str = "NA"
    descricao_artigo: str = "NA"
    cadencia_artigo: int = 6000
    contagem_atual: int = 0
    contagem_total: int = 0
    quebras: int = 0
    estado: int = 0  # 0: Parado, 1: Contagem, 2: Pausa
    porta_estado: int = 0  # 0: Fechado, 1: Aberto
    ordem: str = "NA"
    configurado: bool = False
    id_ordem: int = 0

    # Estatísticas
    tempo_inicio: Optional[datetime] = None
    tempo_fim: Optional[datetime] = None
    estatistica_gfa: List[float] = field(default_factory=list)
    estatistica_media: List[float] = field(default_factory=list)
    estatistica_nominal: float = 0
    estatistica_tempo: List[str] = field(default_factory=list)
    estatistica_cadencia: List[int] = field(default_factory=list)
    paragens: List[str] = field(default_factory=list)
    registo_paragem: int = 0
    pausa_automatica: bool = False  # Novo campo para controlar pausas automáticas


class Contador:
    def __init__(self, gpio_handler: GPIOHandler, db_manager: DatabaseManager):
        self.state = ContadorState()
        self.gpio = gpio_handler
        self.db = db_manager
        self._running = False
        self._threads = []
        self._last_count = 0
        self._last_time = time.time()
        self._threads = []

    def start(self):
        """Inicia todas as threads do contador"""
        if not self._running:
            self._running = True
            self._threads = [
                threading.Thread(target=self._contagem_loop, daemon=True),
                threading.Thread(target=self._stats_loop, daemon=True),
                threading.Thread(target=self._schedule_pause_loop, daemon=True)
                # threading.Thread(target=self._auto_pause_loop, daemon=True),
            ]
            for thread in self._threads:
                logging.info(f"Iniciando thread: {thread.name}")
                thread.start()

    def stop(self):
        """Para todas as threads de forma segura"""
        self._running = False
        for thread in self._threads:
            thread.join()
        self.gpio.cleanup()

    def get_status(self) -> Dict[str, Any]:
        """Retorna o estado atual do contador"""
        return {
            "artigo": self.state.artigo,
            "descricao": self.state.descricao_artigo,
            "cadencia": self.state.cadencia_artigo,
            "contagem": self.state.contagem_atual,
            "total": self.state.contagem_total,
            "quebras": self.state.quebras,
            "estado": self.state.estado,
            "porta": self.state.porta_estado,
            "ordem": self.state.ordem,
            "configurado": self.state.configurado,
            "estatisticas": {
                "gfa": self.state.estatistica_gfa[-1]
                if self.state.estatistica_gfa
                else 0,
                "media": self.state.estatistica_media[-1]
                if self.state.estatistica_media
                else 0,
                "nominal": self.state.estatistica_nominal,
            },
        }

    def iniciar_contagem(self):
        """Inicia a contagem"""
        if not self.state.configurado:
            raise ValueError("Contador não configurado")
        self.state.estado = 1
        self.state.tempo_inicio = datetime.now()
        self.state.estatistica_gfa = []
        self.state.estatistica_media = []
        self.state.estatistica_tempo = []
        self.state.paragens = []
        self.gpio.set_door(True)

    def parar_contagem(self):
        """Para a contagem"""
        try:
            if self.state.estado != 0:  # Evita parar múltiplas vezes
                self.state.estado = 0
                self.state.configurado = 0
                self.state.tempo_fim = datetime.now()
                self.gpio.set_door(False)
                self._gravar_dados_finais()
        except Exception as e:
            logging.error(f"Erro ao parar contagem: {e}")

    def pausar_contagem(self):
        """Pausa a contagem"""
        if self.state.estado == 1:
            self.state.estado = 2
            self.state.registo_paragem = 1
            self.gpio.set_door(False)

    def retomar_contagem(self):
        """Retoma a contagem após pausa"""
        if self.state.estado == 2:
            self.state.estado = 1
            self.state.pausa_automatica = False
            self.gpio.set_door(True)

    def configurar_ordem(self, dados: Dict[str, Any]):
        """Configura uma nova ordem de produção"""
        self.state.artigo = dados["artigo"]
        self.state.descricao_artigo = dados["descricao"]
        self.state.cadencia_artigo = int(dados["cadencia"])
        self.state.contagem_total = int(dados["total"])
        self.state.ordem = dados["ordem"]
        self.state.id_ordem = int(dados["id_ordem"])
        self.state.configurado = True
        self.state.contagem_atual = 0
        self.state.quebras = 0

    def adicionar_quebras(self, quantidade: int):
        """Adiciona quebras à contagem"""
        self.state.quebras += quantidade

    def _contagem_loop(self):
        """Loop principal de contagem otimizado"""
        ultimo_estado = False
        contagem_buffer = 0
        ultima_atualizacao = time.time()

        while self._running:
            if self.state.estado == 1:  # Estado de contagem
                estado_atual = self.gpio.read_counter()
                if estado_atual and not ultimo_estado:
                    contagem_buffer += 1

                    # Atualiza a cada 10 contagens ou 1 segundo
                    agora = time.time()
                    if contagem_buffer >= 10 or (agora - ultima_atualizacao) >= 1:
                        self.state.contagem_atual += contagem_buffer
                        if self.state.contagem_atual >= (
                            self.state.contagem_total + self.state.quebras
                        ):
                            self.parar_contagem()

                        contagem_buffer = 0
                        ultima_atualizacao = agora

                ultimo_estado = estado_atual
            time.sleep(0.0001)  # Reduz uso de CPU mantendo resposta rápida

    def _stats_loop(self):
        """Loop de estatísticas otimizado"""
        ultima_gravacao = time.time()

        while self._running:
            if self.state.estado == 1:
                agora = time.time()
                # Grava contagem a cada 10 segundos
                if agora - ultima_gravacao >= 10:  # Alterado de 300 para 10 segundos
                    try:
                        self.db.gravar_contagem(
                            self,
                            self.state.id_ordem,
                            self.state.contagem_atual,
                            self.state.contagem_total,
                        )
                        ultima_gravacao = agora
                    except Exception as e:
                        logging.error(f"Erro ao gravar contagem parcial: {e}")

                contagem_atual = self.state.contagem_atual
                delta_tempo = agora - self._last_time
                delta_contagem = contagem_atual - self._last_count

                if delta_tempo >= 10:  # Mantido em 10 segundos para consistência
                    gfa = (delta_contagem / delta_tempo) * 3600

                    self.state.estatistica_gfa.append(int(gfa))
                    self.state.estatistica_nominal = int(gfa)
                    self.state.estatistica_media.append(
                        int(np.mean(self.state.estatistica_gfa[-10:]))
                    )
                    self.state.estatistica_tempo.append(
                        datetime.now().strftime("%H:%M:%S")
                    )
                    self.state.estatistica_cadencia.append(self.state.cadencia_artigo)

                    # Registra paragem se necessário
                    if self.state.registo_paragem:
                        self.state.paragens.append("0")
                        self.state.registo_paragem = 0
                    else:
                        self.state.paragens.append("null")

                    self._last_count = contagem_atual
                    self._last_time = agora

            time.sleep(1)

    def _auto_pause_loop(self):
        """Loop para detectar paradas automáticas"""
        JANELA_ANALISE = 6  # Analisa 1 minuto (6 períodos de 10 segundos)
        LIMITE_GFA = 100  # Limite mínimo de GFA para considerar produção ativa

        while self._running:
            try:
                if self.state.estado == 1:
                    if len(self.state.estatistica_gfa) >= JANELA_ANALISE:
                        # Analisa os últimos 6 registros (1 minuto)
                        ultimas_gfas = self.state.estatistica_gfa[-JANELA_ANALISE:]
                        media_gfa = sum(ultimas_gfas) / len(ultimas_gfas)

                        # Pausa se a média de GFA estiver abaixo do limite por 1 minuto
                        if media_gfa < LIMITE_GFA:
                            logging.info(
                                f"Pausa automática ativada - GFA média: {media_gfa:.2f}"
                            )
                            self.pausar_contagem()

                time.sleep(10)  # Verifica a cada 10 segundos
            except Exception as e:
                logging.error(f"Erro no loop de pausa automática: {e}")
                time.sleep(10)

    def _schedule_pause_loop(self):
        """Loop para pausar automaticamente nos horários programados"""
        PAUSA_ALMOCO = datetime_time(12, 0)  # 12:00
        PAUSA_FIM = datetime_time(17, 0)  # 17:00

        while self._running:
            try:
                agora = datetime.now().time()

                if self.state.estado == 1 and not self.state.pausa_automatica:
                    if (
                        agora.hour == PAUSA_ALMOCO.hour
                        and agora.minute == PAUSA_ALMOCO.minute
                    ):
                        logging.info("Pausa automática - Horário de almoço")
                        self.state.pausa_automatica = True
                        self.pausar_contagem()

                    elif (
                        agora.hour == PAUSA_FIM.hour
                        and agora.minute == PAUSA_FIM.minute
                    ):
                        logging.info("Pausa automática - Fim de expediente")
                        self.state.pausa_automatica = True
                        self.pausar_contagem()

                time.sleep(30)  # Verifica a cada 30 segundos

            except Exception as e:
                logging.error(f"Erro no loop de pausa programada: {e}")
                time.sleep(60)  # Em caso de erro, espera 1 minuto

    def _gravar_dados_finais(self):
        """Grava os dados finais da produção no banco de dados"""
        try:
            with pymssql.connect(self.db._host, self.db._user, self.db._password, "SIP") as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE krones_contadoreslinha 
                        SET
                            Ativo = 0,
                            QuantidadeFinal = %d,
                            Quebras = %d,
                            MediaProducao = %d,
                            Abertura = %s,
                            Fecho = %s
                        WHERE
                            Ativo = 1 AND
                            Ordem = %s
                    """,
                        (
                            int(self.state.contagem_atual),
                            int(self.state.quebras),
                            int(self.state.estatistica_media[-1] if self.state.estatistica_media else 0),
                            self.state.tempo_inicio,
                            self.state.tempo_fim,
                            str(self.state.ordem),
                        ),
                    )
                conn.commit()
        except Exception as e:
            logging.error(f"Erro ao gravar dados finais: {e}")
            raise

    def reset(self):
        """Reseta o contador para o estado inicial"""
        try:
            self.db.desativar_ordens_ativas()
            self.state = ContadorState()
            self.gpio.set_door(False)
        except Exception as e:
            logging.error(f"Erro ao resetar contador: {e}")
            raise

    def set_porta(self, estado: bool):
        """Controla o estado da porta - simplificado e direto"""
        self.gpio.set_door(estado)
        self.state.porta_estado = 1 if estado else 0
