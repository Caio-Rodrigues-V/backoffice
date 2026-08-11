import sys
import os

# Adiciona a pasta do projeto ao path de importações do Python
sys.path.insert(0, os.path.dirname(__file__))

# Importa o 'app' do Flask do arquivo app.py e renomeia para 'application' (como o Passenger exige)
from app import app as application
