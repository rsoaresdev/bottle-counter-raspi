import logging
import RPi.GPIO as GPIO
from .config import gpio_config
import time


class GPIOHandler:
    def __init__(self):
        self.counter_pin = gpio_config.counter_pin
        self.door_pin = gpio_config.door_pin
        self.door_state = 0  # Adiciona variável para controlar o estado da porta
        self._setup_gpio()
        logging.info("GPIO Handler iniciado")

    def _setup_gpio(self):
        """Configura os pinos GPIO"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)  # Desativa avisos

        # Configura pinos
        GPIO.setup(self.door_pin, GPIO.OUT)
        GPIO.setup(self.counter_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Garante que a porta começa fechada
        GPIO.output(self.door_pin, GPIO.LOW)

    def read_counter(self) -> bool:
        """Lê o estado do contador"""
        return GPIO.input(self.counter_pin)

    def set_door(self, state: bool):
        """Controla a porta/pistão"""
        try:
            GPIO.output(self.door_pin, GPIO.HIGH if state else GPIO.LOW)
            self.door_state = 1 if state else 0  # Atualiza o estado interno
            time.sleep(0.1)  # Pequeno delay para garantir a operação
        except Exception as e:
            logging.error(f"Erro ao controlar porta: {e}")
            raise

    def cleanup(self):
        """Limpa os recursos GPIO"""
        GPIO.cleanup()
