#!/bin/bash

# Definir diretório base
BASE_DIR="/home/pi/krones"
cd $BASE_DIR

# Atualizar e instalar dependências
echo "Instalando dependências do sistema..."
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    python3-rpi.gpio

# Criar ambiente virtual
echo "Configurando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Criar diretórios necessários
mkdir -p logs

# Configurar permissões
echo "Configurando permissões..."
sudo chown -R root:root .
sudo chmod 755 .
sudo chmod 600 certs/CERT.key
sudo chmod 644 certs/CERT.crt

# Configurar serviço
echo "Configurando serviço systemd..."
sudo cat > /etc/systemd/system/krones-counter.service << EOL
[Unit]
Description=Krones Counter Service
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${BASE_DIR}
Environment=VIRTUAL_ENV=${BASE_DIR}/venv
Environment=PATH=${BASE_DIR}/venv/bin:${PATH}
Environment=PYTHONPATH=${BASE_DIR}
ExecStart=${BASE_DIR}/venv/bin/python ${BASE_DIR}/main.py
Restart=always
RestartSec=5
StandardOutput=append:${BASE_DIR}/logs/service.log
StandardError=append:${BASE_DIR}/logs/service.log

[Install]
WantedBy=multi-user.target
EOL

# Recarregar e reiniciar serviços
echo "Reiniciando serviços..."
sudo systemctl daemon-reload
sudo systemctl restart krones-counter.service

# Configurar watchdog
echo "Configurando watchdog..."
sudo cat > /etc/systemd/system/krones-watchdog.service << EOL
[Unit]
Description=Krones Counter Watchdog
After=krones-counter.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${BASE_DIR}
Environment=VIRTUAL_ENV=${BASE_DIR}/venv
Environment=PATH=${BASE_DIR}/venv/bin:${PATH}
Environment=PYTHONPATH=${BASE_DIR}
ExecStart=${BASE_DIR}/venv/bin/python ${BASE_DIR}/src/watchdog.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable krones-watchdog.service
sudo systemctl restart krones-watchdog.service

echo "Instalação concluída!" 