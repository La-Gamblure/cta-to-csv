# CTA to CSV - Version Focus

Version simplifiée de l'application CTA to CSV qui se concentre sur la fonctionnalité essentielle : récupérer les NFTs de Cross The Ages (CTA) d'une adresse ImmutableX et générer un CSV avec les quantités par grade.

## Fonctionnalités

- Interface utilisateur minimaliste
- Récupération des NFTs CTA via l'API ImmutableX
- Génération d'un CSV avec les colonnes suivantes :
  - Nom du NFT
  - Rareté
  - Élément
  - Avancement
  - Faction
  - Quantités par grade (Standard, C, B, A, S)
  - Quantités par grade en version foil

## Utilisation

1. Entrez une adresse ImmutableX valide
2. Cliquez sur "Générer CSV"
3. Attendez que les NFTs soient récupérés
4. Téléchargez le CSV généré

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/La-Gamblure/cta-to-csv.git

# Accéder au répertoire du projet
cd cta-to-csv

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
cd cta-to-csv/focus-version
python app.py
```

L'application sera accessible à l'adresse http://127.0.0.1:5010
