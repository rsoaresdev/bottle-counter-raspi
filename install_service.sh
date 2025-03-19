#!/bin/bash

# Criar o arquivo de serviço
sudo cat > /etc/systemd/system/krones-counter.service << EOL
[Unit]
Description=Krones Counter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/krones
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
StandardOutput=append:/home/pi/krones/logs/service.log
StandardError=append:/home/pi/krones/logs/service.log

[Install]
WantedBy=multi-user.target
EOL

# Recarregar o systemd
sudo systemctl daemon-reload

# Habilitar o serviço para iniciar com o boot
sudo systemctl enable krones-counter.service

# Iniciar o serviço
sudo systemctl start krones-counter.service 