from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
import requests
import json
import csv
import io
import re
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_nfts', methods=['POST'])
def get_nfts():
    address = request.form.get('address')
    
    # Validation de l'adresse Ethereum
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'error': 'Adresse Ethereum invalide'}), 400
    
    try:
        # Récupération des NFTs via l'API ImmutableX
        response = requests.get(f'https://api.x.immutable.com/v1/assets?user={address}&status=imx&page_size=100')
        data = response.json()
        
        if 'result' not in data:
            return jsonify({'error': 'Aucun NFT trouvé ou erreur API'}), 404
        
        nfts = data['result']
        
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
            download_name=f'nfts_{address}.csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
