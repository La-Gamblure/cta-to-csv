import sys
import os

# Ajouter le sous-dossier au chemin Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cta-to-csv'))

# Importer l'application Flask
from app import app

# Nécessaire pour que Gunicorn trouve l'application
if __name__ == '__main__':
    app.run()
