from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    host: str = ""  # IP do servidor MySQL
    user: str = ""
    password: str = ""
    port: int = 1433  # Porta padrão do MySQL

@dataclass
class AppConfig:
    debug: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    host: str = os.getenv('APP_HOST', '0.0.0.0')  # Este é o host da API
    port: int = int(os.getenv('APP_PORT', 443))
    base_path: Path = Path(os.getenv('BASE_PATH', os.getcwd()))  # Usa o diretório atual por padrão
    log_path: Path = base_path / 'logs' / 'app.log'
    cert_path: Path = base_path / 'certs' / 'CERT.crt'
    key_path: Path = base_path / 'certs' / 'CERT.key'

@dataclass
class GPIOConfig:
    counter_pin: int = int(os.getenv('COUNTER_PIN', 22))
    door_pin: int = int(os.getenv('DOOR_PIN', 23))

# Instâncias das configurações
db_config = DatabaseConfig()
app_config = AppConfig()
gpio_config = GPIOConfig() 