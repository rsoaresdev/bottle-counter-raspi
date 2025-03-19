from flask import Flask, jsonify
from flask_cors import CORS
from .contador import Contador
import logging
from datetime import datetime, timedelta
import math
import numpy as np
import pymssql


def create_app(contador: Contador) -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route("/abrir-porta", methods=["GET"])
    def abrir_porta():
        contador.set_porta(True)
        return jsonify({"status": "OK"}), 200

    @app.route("/fechar-porta", methods=["GET"])
    def fechar_porta():
        contador.set_porta(False)
        return jsonify({"status": "OK"}), 200

    @app.route("/iniciar-contagem", methods=["GET"])
    def iniciar_contagem():
        contador.iniciar_contagem()
        return jsonify({"status": "OK"}), 200

    @app.route("/parar-contagem", methods=["GET"])
    def parar_contagem():
        contador.parar_contagem()
        return jsonify({"status": "OK"}), 200

    @app.route("/pausa", methods=["GET"])
    def pausa():
        contador.pausar_contagem()
        return jsonify({"status": "OK"}), 200

    @app.route("/retomar", methods=["GET"])
    def retomar():
        contador.retomar_contagem()
        return jsonify({"status": "OK"}), 200

    @app.route("/quebra/<int:valor>", methods=["GET"])
    def quebra(valor):
        try:
            if contador.state.estado == 1:
                contador.adicionar_quebras(valor)
                return jsonify({"status": "OK"}), 200
            return jsonify({"message": "Contador não está em contagem"}), 400
        except Exception as e:
            logging.error(f"Erro ao registrar quebra: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/setup/<string:ordem>/<int:cnt>", methods=["GET"])
    def setup_contagem(ordem, cnt):
        try:
            dados = contador.db.buscar_ordem_producao(ordem)
            if dados:
                contador.configurar_ordem(
                    {
                        "artigo": dados["Artigo"],
                        "descricao": dados["DescricaoArtigo"],
                        "cadencia": dados["CadenciaArtigo"],
                        "total": cnt,
                        "ordem": ordem,
                        "id_ordem": dados["Id"],
                    }
                )
                
                # Registrar na base de dados
                with pymssql.connect(contador.db._host, contador.db._user, contador.db._password, "SIP") as conn:
                    with conn.cursor() as cursor:
                        # Inserir nova ordem de produção
                        sql_insert = """
                            INSERT INTO krones_contadoreslinha
                                (Data, Ativo, Ordem, QuantidadeInicial, Artigo)
                            VALUES
                                (%s, %s, %s, %s, %s)
                        """
                        
                        data_insert = (
                            datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
                            1,
                            ordem,
                            cnt,
                            dados["Artigo"]
                        )
                        
                        cursor.execute(sql_insert, data_insert)
                        conn.commit()              
                return jsonify(
                    {"message": f"Ordem {ordem} configurada com {cnt} garrafas totais"}
                ), 200
            return jsonify({"error": "Ordem não encontrada ou já finalizada"}), 404
        except Exception as e:
            logging.error(f"Erro ao configurar contagem: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/reset-contador", methods=["GET"])
    def reset_contador():
        if contador.state.estado == 0:
            try:
                contador.reset()
                return jsonify({"message": "OK"}), 200
            except Exception as e:
                logging.error(f"Erro ao resetar contador: {e}")
                return jsonify({"message": "Erro ao resetar contador"}), 500
        return jsonify({"message": "Contador não está parado"}), 400

    @app.route("/status", methods=["GET"])
    def status():
        media = (
            round(np.mean(contador.state.estatistica_gfa))
            if contador.state.estatistica_gfa
            else 0
        )
        data = {
            "Ordem": contador.state.ordem,
            "Artigo": contador.state.artigo,
            "DescricaoArtigo": contador.state.descricao_artigo,
            "CadenciaArtigo": contador.state.cadencia_artigo,
            "Inicio": contador.state.tempo_inicio.strftime("%Y-%m-%d %H:%M:%S")
            if contador.state.tempo_inicio
            else "",
            "Fim": contador.state.tempo_fim.strftime("%Y-%m-%d %H:%M:%S")
            if contador.state.tempo_fim
            else "",
            "ContagemAtual": contador.state.contagem_atual,
            "ContagemTotal": contador.state.contagem_total,
            "MediaProducao": media,
            "Nominal": contador.state.estatistica_nominal,
            "Quebras": contador.state.quebras,
            "EstadoPorta": contador.gpio.door_state,
            "EstadoContador": contador.state.estado,
            "EstadoConfiguracao": contador.state.configurado,
            "IdBDOrdemProducao": contador.state.id_ordem,
        }
        return jsonify({"data": data}), 200

    @app.route("/api/info", defaults={"NumPontos": 180, "Ordem": None})
    @app.route("/api/info/<int:NumPontos>/<string:Ordem>")
    def ApiInfo(NumPontos, Ordem):
        media = (
            round(np.mean(contador.state.estatistica_gfa))
            if contador.state.estatistica_gfa
            else 0
        )
        estimativa_tempo = None

        if media > 0 and contador.state.estado == 1:
            minutos = math.ceil(
                (contador.state.contagem_total - contador.state.contagem_atual)
                * 60
                / media
            )
            estimativa_tempo = (
                datetime.now() + timedelta(minutes=minutos)
            ).strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "DataDados": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Ordem": contador.state.ordem,
            "Artigo": contador.state.artigo,
            "DescricaoArtigo": contador.state.descricao_artigo,
            "CadenciaArtigo": contador.state.cadencia_artigo,
            "Inicio": contador.state.tempo_inicio.strftime("%Y-%m-%d %H:%M:%S")
            if contador.state.tempo_inicio
            else "",
            "Fim": contador.state.tempo_fim.strftime("%Y-%m-%d %H:%M:%S")
            if contador.state.tempo_fim
            else "",
            "ContagemAtual": contador.state.contagem_atual,
            "ContagemTotal": contador.state.contagem_total,
            "MediaProducao": media,
            "EstimativaFecho": estimativa_tempo,
            "Nominal": contador.state.estatistica_gfa,
            "Paragens": contador.state.paragens,
            "Quebras": contador.state.quebras,
            "EstadoPorta": contador.gpio.door_state,
            "EstadoContador": contador.state.estado,
            "EstadoConfiguracao": contador.state.configurado,
            "Media": contador.state.estatistica_media,
            "Cadencia": contador.state.estatistica_cadencia,
            "Tempo": contador.state.estatistica_tempo,
            "IdBDOrdemProducao": contador.state.id_ordem,
        }
        return jsonify(data), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Rota não encontrada"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logging.error(e)
        return jsonify({"error": "Erro interno do servidor"}), 500

    return app
