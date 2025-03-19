# Contador de Garrafas em Python para Raspberry Pi com Sensores Laser

## Descrição
Este projeto consiste num sistema de contagem de garrafas utilizando um Raspberry Pi, sensores laser e uma interface api baseada em Flask. O sistema regista as contagens, controla a abertura e fechamento do pistão, e armazena dados numa base de dados.

## Funcionalidades
- **Contagem de Garrafas:** Utiliza sensores laser para contar garrafas.
- **Controle de Porta:** Abre e fecha a porta automaticamente durante a contagem.
- **Interface Web:** API RESTful para iniciar, pausar, retomar e parar a contagem, além de configurar o contador.
- **Registo de Dados:** Armazena as contagens e estatísticas numa base de dados.
- **Logging:** Regista atividades e eventos do sistema.

## Tecnologias Utilizadas
- Python
- Flask
- GPIO (Controlo de periféricos do Raspberry Pi)
- pymssql (para conexão com a base de dados SQL Server)
- NumPy
- threading
- logging

## Requisitos
- Raspberry Pi com GPIO configurado
- Sensores laser conectados aos pinos GPIO do Raspberry Pi
- Base de Dados SQL Server
- Python 3.x
- Bibliotecas Python:
    - Flask
    - RPi.GPIO
    - pymssql
    - NumPy

## Configuração
### Conexões GPIO

- Pino 22: Conectado ao sensor de contagem de garrafas.
- Pino 23: Conectado ao controlo da porta (pistão de ar comprimido).

### Base de Dados
Configurar as variáveis de ambiente para conexão com a base de dados:

- `DB_Server`: Endereço do servidor de base de dados.
- `DB_User`: Utilizador da base de dados.
- `DB_Password`: Senha do utilizador da base de dados.
- `DB_DB`: Nome da base de dados.