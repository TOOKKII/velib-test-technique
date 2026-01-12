# Projet Vélib - Visualisation & Gestion

Application Fullstack permettant de visualiser les bornes Vélib de Paris sur une carte interactive et de gérer les stations (CRUD). Ce projet a été réalisé dans le cadre d'un test technique.

## Fonctionnalités

- **Carte Interactive :** Visualisation des stations sur un fond de carte Mapbox.
- **Recherche :** Géocodage d'adresses (API Gouv) pour trouver les stations à proximité.
- **Gestion (CRUD) :** Ajout et suppression de stations via une interface sécurisée.
- **Données :** Importation automatique d'un fichier CSV propriétaire (`velib-pos.csv`).
- **Authentification :** Système de login (Simulé pour le MVP : `admin` / `admin`).

## Stack Technique

**Backend :**
- Python 3.10+
- **Flask** (API REST)
- **SQLAlchemy** (ORM & Gestion SQLite)
- **Pandas** (Traitement et nettoyage du CSV)

**Frontend :**
- **React.js** (Create React App)
- **Mapbox GL JS** (Cartographie)
- **Axios** (Requêtes HTTP)
- **React Hook Form** (Gestion des formulaires)

---

## Installation & Lancement local

### Prérequis
- Python installé
- Node.js installé
- Un token public **Mapbox**

### 1. Installation du Backend
```bash
cd backend
# Création de l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Ou venv\Scripts\activate sur Windows

# Installation des dépendances
pip install -r requirements.txt

# Lancement (L'import du CSV se fait au premier lancement)
python app.py
