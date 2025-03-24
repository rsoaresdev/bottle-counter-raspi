import logging
from pathlib import Path
import signal
import sys
from src.config import app_config
from src.contador import Contador
from src.gpio_handler import GPIOHandler
from src.database import DatabaseManager
from src.api import create_app
import ssl

class Application:
    def __init__(self):
        self.contador = None
        self.setup_signal_handlers()
        self.setup_directories()
        self.setup_logging()

    def setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def setup_directories(self):
        Path("logs").mkdir(exist_ok=True)
        Path("certs").mkdir(exist_ok=True)

    def setup_logging(self):
        logging.basicConfig(
            filename=str(app_config.log_path),
            level=logging.INFO,
            format="%(asctime)s;%(levelname)s;%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def handle_shutdown(self, signum, frame):
        logging.info("Recebido sinal de shutdown")
        if self.contador:
            self.contador.stop()
        sys.exit(0)

    def run(self):
        try:
            # Inicializa componentes
            gpio_handler = GPIOHandler()
            db_manager = DatabaseManager()
            self.contador = Contador(gpio_handler, db_manager)

            # Inicia o contador
            self.contador.start()

            # Configura e inicia a API
            app = create_app(self.contador)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.load_cert_chain(
                certfile=str(app_config.cert_path), keyfile=str(app_config.key_path)
            )

            app.run(host=app_config.host, port=app_config.port, ssl_context=context)

        except Exception as e:
            logging.error(f"Erro fatal na aplicação: {e}")
            raise


if __name__ == "__main__":
    app = Application()
    app.run()
