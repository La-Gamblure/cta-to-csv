from flask import Flask, request, render_template, send_file, jsonify
import requests
import json
import csv
import io
import re
import os
import threading
import sys
from collections import defaultdict
from datetime import datetime

# Ajouter le sous-dossier au chemin Python si nécessaire
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cta-to-csv'))

app = Flask(__name__)

# Dictionnaire pour stocker l'état de chaque requête
request_status = {}

# Regex pour valider les adresses Ethereum
ETH_ADDRESS_REGEX = re.compile(r'^0x[a-fA-F0-9]{40}$')

def is_valid_eth_address(address):
    """Vérifie si l'adresse est une adresse Ethereum valide"""
    return bool(ETH_ADDRESS_REGEX.match(address))

def fetch_assets_for_address(address):
    """Récupère les NFTs pour une adresse spécifique depuis l'API ImmutableX avec pagination"""
    assets = []
    cursor = None
    page_size = 200  # Taille de page maximale autorisée
    
    # Initialiser le statut de la requête
    request_status[address] = {
        'status': 'processing',
        'count': 0,
        'assets': [],
        'error': None
    }
    
    try:
        while True:
            url = f"https://api.x.immutable.com/v1/assets?user={address}&page_size={page_size}"
            if cursor:
                url += f"&cursor={cursor}"
            
            try:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code != 200:
                    request_status[address]['status'] = 'error'
                    request_status[address]['error'] = f"Erreur API: {response.status_code}"
                    return []
                
                data = response.json()
                
                if 'result' not in data:
                    break
                
                batch = data['result']
                if not batch:
                    break
                
                assets.extend(batch)
                request_status[address]['count'] = len(assets)
                request_status[address]['assets'] = assets
                
                # Vérifier s'il y a une page suivante
                cursor = data.get('cursor')
                if not cursor:
                    break
                
                # Pause pour éviter de surcharger l'API
                import time
                time.sleep(0.5)
                
            except Exception as e:
                app.logger.error(f"Erreur lors de la récupération des NFTs: {str(e)}")
                request_status[address]['status'] = 'error'
                request_status[address]['error'] = str(e)
                return assets
        
        request_status[address]['status'] = 'processing_complete'
        return assets
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des NFTs: {str(e)}")
        request_status[address]['status'] = 'error'
        request_status[address]['error'] = str(e)
        return assets

def process_assets(assets):
    """Traite les NFTs pour extraire les informations nécessaires"""
    processed_data = []
    
    for asset in assets:
        try:
            # Extraire les métadonnées
            metadata = asset.get('metadata', {})
            
            # Extraire les informations de base
            name = metadata.get('name', '')
            rarity = metadata.get('rarity', '')
            element = metadata.get('element', '')
            advancement = metadata.get('advancement', 'STANDARD')
            faction = metadata.get('faction', '')
            grade = metadata.get('grade', '')
            is_foil = metadata.get('foil', False)
            
            # Ajouter à la liste des données traitées
            processed_data.append({
                'name': name,
                'rarity': rarity,
                'element': element,
                'advancement': advancement,
                'faction': faction,
                'grade': grade,
                'is_foil': is_foil
            })
            
        except Exception as e:
            app.logger.error(f"Erreur lors du traitement d'un NFT: {e}")
            continue
    
    return processed_data

def generate_csv(processed_data):
    """Génère un fichier CSV avec les données traitées"""
    # Définir l'ordre des raretés pour le tri
    RARITY_ORDER = {
        'MYTHIC': 1,
        'ULTRA_RARE': 2, 
        'SPECIAL_RARE': 3,
        'RARE': 4,
        'UNCOMMON': 5,
        'COMMON': 6,
        'EXCLUSIVE': 7
    }

    # Définir l'ordre des avancements pour le tri
    ADVANCEMENT_ORDER = {
        'COMBO': 1,
        'ALTERNATIVE': 2,
        'STANDARD': 3
    }
    
    # Créer une structure pour stocker les comptages
    # Clé: (nom, rareté, élément, avancement, faction)
    # Valeur: compteurs pour Standard, C, B, A, S et leurs versions foil
    counts = defaultdict(lambda: {
        'Standard': 0, 'C': 0, 'B': 0, 'A': 0, 'S': 0,
        'foil_Standard': 0, 'foil_C': 0, 'foil_B': 0, 'foil_A': 0, 'foil_S': 0
    })
    
    # Compter les cartes par nom, rareté, élément, avancement et faction
    for item in processed_data:
        name = item['name']
        rarity = item['rarity']
        element = item['element']
        advancement = item['advancement']
        faction = item['faction']
        grade = item['grade']
        is_foil = item['is_foil']
        
        key = (name, rarity, element, advancement, faction)
        
        if not grade:  # Si grade est vide, c'est Standard
            counts[key]['Standard'] += 1
            if is_foil:
                counts[key]['foil_Standard'] += 1
        elif grade in ['C', 'B', 'A', 'S']:
            counts[key][grade] += 1
            if is_foil:
                counts[key][f'foil_{grade}'] += 1
    
    # Convertir en liste pour le tri
    result = []
    for (name, rarity, element, advancement, faction), grades in counts.items():
        result.append({
            'nom': name,
            'rareté': rarity,
            'élément': element,
            'avancement': advancement,
            'faction': faction,
            'Standard': grades['Standard'],
            'C': grades['C'],
            'B': grades['B'],
            'A': grades['A'],
            'S': grades['S'],
            'foil_Standard': grades['foil_Standard'],
            'foil_C': grades['foil_C'],
            'foil_B': grades['foil_B'],
            'foil_A': grades['foil_A'],
            'foil_S': grades['foil_S']
        })
    
    # Trier par rareté puis par avancement
    result.sort(key=lambda x: (
        RARITY_ORDER.get(x['rareté'], 999),
        ADVANCEMENT_ORDER.get(x['avancement'], 999)
    ))
    
    # Créer un fichier CSV en mémoire
    output = io.StringIO()
    fieldnames = [
        'nom', 'rareté', 'élément', 'avancement', 'faction',
        'Standard', 'C', 'B', 'A', 'S',
        'foil_Standard', 'foil_C', 'foil_B', 'foil_A', 'foil_S'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(result)
    
    return output.getvalue()

def process_address_async(address):
    """Traite l'adresse de manière asynchrone"""
    assets = fetch_assets_for_address(address)
    if assets:
        processed_data = process_assets(assets)
        csv_content = generate_csv(processed_data)
        request_status[address]['csv_content'] = csv_content
        request_status[address]['status'] = 'complete'
    else:
        if request_status[address]['status'] != 'error':
            request_status[address]['status'] = 'error'
            request_status[address]['error'] = "Aucun NFT trouvé"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    address = request.form.get('address')
    
    if not address:
        return jsonify({'error': 'Adresse non fournie'}), 400
    
    if not is_valid_eth_address(address):
        return jsonify({'error': 'Adresse Ethereum invalide'}), 400
    
    # Vérifier si un traitement est déjà en cours pour cette adresse
    if address in request_status and request_status[address]['status'] in ['processing', 'processing_complete']:
        return jsonify({'message': 'Traitement déjà en cours', 'address': address}), 200
    
    # Initialiser le statut
    request_status[address] = {
        'status': 'processing',
        'count': 0,
        'assets': [],
        'error': None
    }
    
    # Démarrer le traitement dans un thread séparé
    thread = threading.Thread(target=process_address_async, args=(address,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Traitement démarré', 'address': address}), 200

@app.route('/status', methods=['GET'])
def status():
    address = request.args.get('address')
    
    if not address:
        return jsonify({'error': 'Adresse non fournie'}), 400
    
    if address not in request_status:
        return jsonify({'error': 'Aucun traitement en cours pour cette adresse'}), 404
    
    status_data = {
        'status': request_status[address]['status'],
        'count': request_status[address]['count'],
        'error': request_status[address]['error']
    }
    
    return jsonify(status_data), 200

@app.route('/download', methods=['GET'])
def download():
    address = request.args.get('address')
    
    if not address:
        return jsonify({'error': 'Adresse non fournie'}), 400
    
    if address not in request_status:
        return jsonify({'error': 'Aucun traitement en cours pour cette adresse'}), 404
    
    if request_status[address]['status'] != 'complete':
        return jsonify({'error': 'Le traitement n\'est pas terminé'}), 400
    
    if 'csv_content' not in request_status[address]:
        return jsonify({'error': 'Aucun contenu CSV disponible'}), 404
    
    # Créer un fichier CSV à partir du contenu stocké
    output = io.StringIO(request_status[address]['csv_content'])
    
    # Préparation du fichier à télécharger
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'nfts_{address}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

# Garder cette route pour la compatibilité avec les anciens appels
@app.route('/get_nfts', methods=['POST'])
def get_nfts():
    return process()

if __name__ == '__main__':
    app.run(debug=True)
