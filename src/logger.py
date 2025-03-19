import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import app_config


def setup_logger():
    """Configura o logger da aplicação"""
    # Cria o diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configura o handler de arquivo com rotação
    file_handler = RotatingFileHandler(
        str(app_config.log_path),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
    )

    # Configura o formato do log
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Configura o logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Também envia logs para o console em modo debug
    if app_config.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
