import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import os


class ServiceWatchdog:
    def __init__(self):
        self.service_name = "krones-counter"
        self.log_path = Path("/home/pi/krones/logs")
        self.setup_logging()

    def setup_logging(self):
        """Configura o sistema de logging com rotação de arquivos"""
        self.log_path.mkdir(exist_ok=True)
        
        # Log do serviço principal
        service_handler = RotatingFileHandler(
            self.log_path / "service.log",
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
        service_handler.setFormatter(
            logging.Formatter('%(asctime)s;%(levelname)s;%(message)s')
        )
        
        # Log do watchdog
        watchdog_handler = RotatingFileHandler(
            self.log_path / "watchdog.log",
            maxBytes=1024 * 1024,
            backupCount=5
        )
        watchdog_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )

        # Configurar loggers
        service_logger = logging.getLogger('service')
        service_logger.setLevel(logging.INFO)
        service_logger.addHandler(service_handler)

        watchdog_logger = logging.getLogger('watchdog')
        watchdog_logger.setLevel(logging.INFO)
        watchdog_logger.addHandler(watchdog_handler)

    def check_service(self):
        """Verifica se o serviço está rodando"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == "active"
        except Exception as e:
            logging.getLogger('watchdog').error(f"Erro ao verificar serviço: {e}")
            return False

    def restart_service(self):
        """Reinicia o serviço se necessário"""
        try:
            subprocess.run(["sudo", "systemctl", "restart", self.service_name])
            logging.getLogger('watchdog').info("Serviço reiniciado")
        except Exception as e:
            logging.getLogger('watchdog').error(f"Erro ao reiniciar serviço: {e}")

    def check_system_resources(self):
        """Verifica recursos do sistema"""
        try:
            # Verifica uso de CPU
            cpu_usage = os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip()
            
            # Verifica memória livre
            free_memory = os.popen("free -m | awk '/Mem:/ {print $4}'").readline().strip()
            
            if float(cpu_usage) > 90 or int(free_memory) < 50:
                logging.getLogger('watchdog').warning(f"Recursos críticos - CPU: {cpu_usage}%, Memória livre: {free_memory}MB")
                self.restart_service()
        except Exception as e:
            logging.getLogger('watchdog').error(f"Erro ao verificar recursos: {e}")

    def run(self):
        """Loop principal do watchdog"""
        while True:
            if not self.check_service():
                logging.getLogger('watchdog').warning("Serviço não está rodando")
                self.restart_service()
            self.check_system_resources()
            time.sleep(60)  # Verifica a cada minuto


if __name__ == "__main__":
    watchdog = ServiceWatchdog()
    watchdog.run()
