from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import csv
import json
import urllib.request
import urllib.parse
import io
import re
import os
import time
import threading
from datetime import datetime
import socket

app = Flask(__name__, template_folder='templates')

# Regex pour valider les adresses Ethereum
ETH_ADDRESS_REGEX = re.compile(r'^0x[a-fA-F0-9]{40}$')

def is_valid_eth_address(address):
    """Vérifie si l'adresse est une adresse Ethereum valide"""
    return bool(ETH_ADDRESS_REGEX.match(address))

def fetch_assets_for_address(address):
    """Récupère les NFTs pour une adresse spécifique depuis l'API ImmutableX"""
    try:
        base_url = "https://api.x.immutable.com/v1/assets"
        cursor = ""
        assets = []
        page = 1
        max_pages = 100  # Limite de sécurité pour éviter les boucles infinies
        
        while page <= max_pages:
            params = {
                "user": address,
                "collection": "0xacb3c6a43d15b907e8433077b6d38ae40936fe2c",  # Collection CTA
                "status": "imx",
                "page_size": 200,  # Taille maximale de page
            }
            
            if cursor:
                params["cursor"] = cursor
            
            query_string = urllib.parse.urlencode(params)
            url = f"{base_url}?{query_string}"
            
            req = urllib.request.Request(url, headers={
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            })
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                current_assets = data.get("result", [])
                assets.extend(current_assets)
                
                # Mettre à jour le compteur de progression si un statut de traitement existe pour cette adresse
                if address in processing_status:
                    processing_status[address]["count"] = len(assets)
                
                # Vérifier s'il y a une page suivante
                cursor = data.get("cursor")
                if not cursor:
                    break
                
                page += 1
                # Pause courte pour éviter de surcharger l'API
                time.sleep(0.1)
        
        return {"success": True}, assets
    except Exception as e:
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
    counts = {}
    
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
        
        if key not in counts:
            counts[key] = {
                'Standard': 0, 'C': 0, 'B': 0, 'A': 0, 'S': 0,
                'foil_Standard': 0, 'foil_C': 0, 'foil_B': 0, 'foil_A': 0, 'foil_S': 0
            }
        
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

# Stockage temporaire des statuts de traitement
processing_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['GET', 'POST'])
def process():
    address = request.args.get('address', '') or request.form.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if not is_valid_eth_address(address):
        return jsonify({"error": "Format d'adresse Ethereum invalide. L'adresse doit être au format 0x suivi de 40 caractères hexadécimaux."})
    
    # Initialiser le statut de traitement
    processing_status[address] = {
        "status": "processing",
        "count": 0,
        "error": "",
        "result": ""
    }
    
    # Démarrer le traitement en arrière-plan
    def process_data():
        try:
            # Récupérer les NFTs pour l'adresse
            processing_status[address]["count"] = 0
            status, assets = fetch_assets_for_address(address)
            
            if "error" in status:
                processing_status[address]["error"] = status["error"]
                processing_status[address]["status"] = "error"
                return
            
            # Traiter les NFTs
            processed_data = process_assets(assets)
            
            # Générer le fichier CSV
            csv_data = generate_csv(processed_data)
            
            # Stocker le résultat
            processing_status[address]["result"] = csv_data
            processing_status[address]["status"] = "complete"
            
        except Exception as e:
            processing_status[address]["error"] = str(e)
            processing_status[address]["status"] = "error"
    
    # Lancer le thread de traitement
    thread = threading.Thread(target=process_data)
    thread.daemon = True
    thread.start()
    
    # Rediriger ou répondre avec JSON en fonction du type de requête
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
        # Redirection si c'est un formulaire HTML normal
        return redirect(url_for('index', address=address))
    else:
        # Réponse JSON pour les requêtes AJAX
        return jsonify({"status": "processing", "address": address})

@app.route('/api/status', methods=['GET'])
def api_status():
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if address not in processing_status:
        return jsonify({"error": "Aucun traitement en cours pour cette adresse"})
    
    status = processing_status[address]
    
    return jsonify({
        "status": status["status"],
        "count": status["count"],
        "error": status["error"]
    })

@app.route('/api/download', methods=['GET'])
def api_download():
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if address not in processing_status:
        return jsonify({"error": "Aucun traitement trouvé pour cette adresse"})
    
    status = processing_status[address]
    
    if status["status"] != "complete":
        return jsonify({"error": "Le traitement n'est pas encore terminé"})
    
    try:
        # Créer un fichier en mémoire
        mem_file = io.BytesIO()
        mem_file.write(status["result"].encode('utf-8'))
        mem_file.seek(0)
        
        # Générer un nom de fichier avec timestamp pour éviter les problèmes de cache
        timestamp = int(time.time())
        filename = f"nft_par_nom_rarete_element_{address[:8]}_{timestamp}.csv"
        
        response = send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
        # Ajouter des en-têtes pour éviter la mise en cache
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        return response
    except Exception as e:
        print(f"Erreur lors du téléchargement: {str(e)}")
        return jsonify({"error": f"Erreur lors du téléchargement: {str(e)}"}), 500

@app.route('/api/process', methods=['GET'])
def api_process():
    address = request.args.get('address', '')
    
    if not address:
        return jsonify({"error": "Adresse non spécifiée"})
    
    if not is_valid_eth_address(address):
        return jsonify({"error": "Format d'adresse Ethereum invalide. L'adresse doit être au format 0x suivi de 40 caractères hexadécimaux."})
    
    # Utiliser la route process
    return process()

if __name__ == '__main__':
    app.run(debug=True)
