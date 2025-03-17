import sys
import os

# Ajouter le répertoire du projet au chemin d'importation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importer l'application depuis app.py à la racine
from app import app

if __name__ == "__main__":
    app.run()
