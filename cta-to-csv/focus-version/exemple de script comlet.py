exemple de script comlet


from flask import Flask, request, render_template, send_file, jsonify
import csv
import json
import urllib.request
import urllib.parse
import time
import io
import os
import threading
import re
from collections import defaultdict

app = Flask(__name__)

# Dictionnaire pour stocker l'état de chaque requête
request_status = {}

# Regex pour valider les adresses Ethereum
ETH_ADDRESS_REGEX = re.compile(r'^0x[a-fA-F0-9]{40}$')

def is_valid_eth_address(address):
    """Vérifie si l'adresse est une adresse Ethereum valide"""
    return bool(ETH_ADDRESS_REGEX.match(address))

def fetch_assets_for_address(address):
    """Récupère les NFTs pour une adresse spécifique depuis l'API ImmutableX"""
    assets = []
    cursor = None
    page_size = 200  # Taille de page maximale autorisée
    
    # Initialiser le statut de la requête
    request_status[address] = {
        'status': 'processing',
        'count': 0,
        'assets': []
    }
    
    try:
        while True:
            url = f"https://api.x.immutable.com/v1/assets?user={address}&page_size={page_size}"
            if cursor:
                url += f"&cursor={cursor}"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                
                if 'result' in data:
                    batch = data['result']
                    assets.extend(batch)
                    
                    # Mettre à jour le statut
                    request_status[address]['count'] = len(assets)
                    request_status[address]['assets'] = assets
                    
                    if 'cursor' in data and data['cursor'] and len(batch) > 0:
                        cursor = data['cursor']
                        # Pause pour éviter de surcharger l'API
                        time.sleep(0.5)
                    else:
                        break
                else:
                    break
                    
            except Exception as e:
                print(f"Erreur lors de la récupération des NFTs: {e}")
                request_status[address]['status'] = 'error'
                request_status[address]['error'] = str(e)
                return {"error": str(e)}, []
        
        request_status[address]['status'] = 'complete'
        return {"success": f"Récupération terminée. Nombre total de NFTs: {len(assets)}"}, assets
    
    except Exception as e:
        print(f"Erreur générale: {e}")
        request_status[address]['status'] = 'error'
        request_status[address]['error'] = str(e)
        return {"error": str(e)}, []

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
            print(f"Erreur lors du traitement d'un NFT: {e}")
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
    _, assets = fetch_assets_for_address(address)
    
    # Le statut est mis à jour dans fetch_assets_for_address

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process')
def process():
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if not is_valid_eth_address(address):
        return jsonify({"error": "Format d'adresse Ethereum invalide. L'adresse doit être au format 0x suivi de 40 caractères hexadécimaux."})
    
    # Vérifier si les données sont déjà disponibles
    if address in request_status and request_status[address]['status'] == 'complete':
        assets = request_status[address]['assets']
        
        if not assets:
            return jsonify({"error": "Aucun NFT trouvé pour cette adresse"})
        
        # Traiter les NFTs
        processed_data = process_assets(assets)
        
        # Générer le fichier CSV
        csv_data = generate_csv(processed_data)
        
        # Créer un fichier en mémoire
        mem_file = io.BytesIO()
        mem_file.write(csv_data.encode('utf-8'))
        mem_file.seek(0)
        
        return send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"nft_par_nom_rarete_element_{address[:8]}.csv"
        )
    else:
        # Démarrer le traitement en arrière-plan si ce n'est pas déjà fait
        if address not in request_status or request_status[address]['status'] not in ['processing', 'complete']:
            thread = threading.Thread(target=process_address_async, args=(address,))
            thread.daemon = True
            thread.start()
        
        # Rediriger vers la page d'attente
        return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Endpoint pour vérifier le statut de la récupération des NFTs"""
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if not is_valid_eth_address(address):
        return jsonify({"error": "Format d'adresse Ethereum invalide. L'adresse doit être au format 0x suivi de 40 caractères hexadécimaux."})
    
    # Vérifier si l'adresse est en cours de traitement
    if address not in request_status:
        # Démarrer le traitement en arrière-plan
        thread = threading.Thread(target=process_address_async, args=(address,))
        thread.daemon = True
        thread.start()
        return jsonify({"status": "processing", "count": 0})
    
    # Retourner le statut actuel
    status_data = request_status[address]
    return jsonify({
        "status": status_data['status'],
        "count": status_data['count'],
        "error": status_data.get('error', '')
    })

@app.route('/api/process', methods=['GET'])
def api_process():
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if not is_valid_eth_address(address):
        return jsonify({"error": "Format d'adresse Ethereum invalide. L'adresse doit être au format 0x suivi de 40 caractères hexadécimaux."})
    
    # Récupérer les NFTs pour l'adresse
    status, assets = fetch_assets_for_address(address)
    
    if "error" in status:
        return jsonify(status)
    
    # Traiter les NFTs
    processed_data = process_assets(assets)
    
    # Générer le fichier CSV
    csv_data = generate_csv(processed_data)
    
    # Créer un fichier en mémoire
    mem_file = io.BytesIO()
    mem_file.write(csv_data.encode('utf-8'))
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"nft_par_nom_rarete_element_{address[:8]}.csv"
    )

if __name__ == '__main__':
    app.run(debug=True, port=8081)
