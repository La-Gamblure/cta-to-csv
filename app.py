import sys
import os

# Ajouter le sous-dossier au chemin Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cta-to-csv'))

# Importer l'application Flask depuis le dossier focus_version
from cta_to_csv.focus_version.app import app as application

# Renommer l'application pour la compatibilité avec Gunicorn
app = application

# Nécessaire pour que Gunicorn trouve l'application
if __name__ == '__main__':
    app.run()
