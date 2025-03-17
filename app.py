from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import requests
import json
import csv
import io
import re
import os
from datetime import datetime

app = Flask(__name__)

# Stockage temporaire des résultats
processing_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    address = request.form.get('address')
    
    # Validation de l'adresse Ethereum
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'error': 'Adresse Ethereum invalide'}), 400
    
    # Initialiser le statut du traitement
    processing_status[address] = {
        'status': 'processing',
        'count': 0,
        'error': None,
        'result': []
    }
    
    try:
        # Récupération des NFTs via l'API ImmutableX
        response = requests.get(f'https://api.x.immutable.com/v1/assets?user={address}&status=imx&page_size=100')
        
        # Vérifier si la réponse est valide
        if response.status_code != 200:
            processing_status[address]['status'] = 'error'
            processing_status[address]['error'] = f'Erreur API: {response.status_code}'
            return jsonify({'error': f'Erreur API: {response.status_code}'}), response.status_code
        
        # Essayer de parser la réponse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            processing_status[address]['status'] = 'error'
            processing_status[address]['error'] = f'Erreur de décodage JSON: {str(e)}'
            return jsonify({'error': f'Erreur de décodage JSON: {str(e)}. Contenu: {response.text[:100]}...'}), 500
        
        if 'result' not in data:
            processing_status[address]['status'] = 'error'
            processing_status[address]['error'] = 'Aucun NFT trouvé ou format de réponse inattendu'
            return jsonify({'error': 'Aucun NFT trouvé ou format de réponse inattendu'}), 404
        
        nfts = data['result']
        processing_status[address]['count'] = len(nfts)
        processing_status[address]['result'] = nfts
        processing_status[address]['status'] = 'complete'
        
        return jsonify({'success': True, 'count': len(nfts)})
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des NFTs: {str(e)}")
        processing_status[address]['status'] = 'error'
        processing_status[address]['error'] = str(e)
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@app.route('/status', methods=['GET'])
def status():
    address = request.args.get('address')
    
    if not address or address not in processing_status:
        return jsonify({'error': 'Adresse non trouvée ou traitement non démarré'}), 404
    
    return jsonify({
        'status': processing_status[address]['status'],
        'count': processing_status[address]['count'],
        'error': processing_status[address]['error']
    })

@app.route('/download', methods=['GET'])
def download():
    address = request.args.get('address')
    
    if not address or address not in processing_status:
        return jsonify({'error': 'Adresse non trouvée ou traitement non démarré'}), 404
    
    if processing_status[address]['status'] != 'complete':
        return jsonify({'error': 'Le traitement n\'est pas terminé'}), 400
    
    nfts = processing_status[address]['result']
    
    # Préparation des données CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes CSV
    writer.writerow(['Token ID', 'Collection', 'Name', 'Description', 'Image URL'])
    
    # Données des NFTs
    for nft in nfts:
        token_id = nft.get('token_id', 'N/A')
        collection = nft.get('collection', {}).get('name', 'N/A')
        name = nft.get('name', 'N/A')
        description = nft.get('description', 'N/A')
        image_url = nft.get('image_url', 'N/A')
        
        writer.writerow([token_id, collection, name, description, image_url])
    
    # Préparation du fichier à télécharger
    output.seek(0)
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
