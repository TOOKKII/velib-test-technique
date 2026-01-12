from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import pandas as pd
import json
from geopy.distance import geodesic

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pk.eyJ1IjoieWJvdXJhZ2hkYSIsImEiOiJjbWsxMXB2MTMwMTUxM3NxeDNidnhudmp3In0.UuYNv8tPStrK75eKbELoxA'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///velib.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# ==================== MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    nbBikes = db.Column(db.Integer, default=0)
    nbEBikes = db.Column(db.Integer, default=0)
    nbFreeDocks = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='Operative')

# ==================== AUTH ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token manquant'}), 401
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except Exception as e:
            return jsonify({'message': f'Token invalide: {str(e)}'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# ==================== ROUTES AUTH ====================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_password)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'Utilisateur créé avec succès'}), 201
    except:
        return jsonify({'message': 'Cet utilisateur existe déjà'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password, data['password']):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'username': user.username})
    
    return jsonify({'message': 'Identifiants incorrects'}), 401

# ==================== ROUTES STATIONS ====================
@app.route('/api/stations', methods=['GET'])
@token_required
def get_stations(current_user):
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', 5000, type=int)
    
    if lat and lng:
        all_stations = Station.query.all()
        nearby_stations = []
        
        for station in all_stations:
            distance = geodesic(
                (lat, lng), 
                (station.latitude, station.longitude)
            ).meters
            
            if distance <= radius:
                nearby_stations.append({
                    'id': station.id,
                    'code': station.code,
                    'name': station.name,
                    'latitude': station.latitude,
                    'longitude': station.longitude,
                    'nbBikes': station.nbBikes,
                    'nbEBikes': station.nbEBikes,
                    'nbFreeDocks': station.nbFreeDocks,
                    'status': station.status,
                    'distance': round(distance, 2)
                })
        
        nearby_stations.sort(key=lambda x: x['distance'])
        return jsonify(nearby_stations)
    
    stations = Station.query.limit(100).all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'latitude': s.latitude,
        'longitude': s.longitude,
        'nbBikes': s.nbBikes,
        'nbEBikes': s.nbEBikes,
        'nbFreeDocks': s.nbFreeDocks,
        'status': s.status
    } for s in stations])

@app.route('/api/stations', methods=['POST'])
@token_required
def create_station(current_user):
    data = request.get_json()
    
    existing = Station.query.filter_by(code=data['code']).first()
    if existing:
        return jsonify({'message': 'Une station avec ce code existe déjà'}), 400
    
    new_station = Station(
        code=data['code'],
        name=data['name'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        nbBikes=data.get('nbBikes', 0),
        nbEBikes=data.get('nbEBikes', 0),
        nbFreeDocks=data.get('nbFreeDocks', 0),
        status=data.get('status', 'Operative')
    )
    db.session.add(new_station)
    db.session.commit()
    return jsonify({'message': 'Station créée avec succès', 'id': new_station.id}), 201

@app.route('/api/stations/<int:id>', methods=['PUT'])
@token_required
def update_station(current_user, id):
    station = Station.query.get_or_404(id)
    data = request.get_json()
    
    station.name = data.get('name', station.name)
    station.latitude = data.get('latitude', station.latitude)
    station.longitude = data.get('longitude', station.longitude)
    station.nbBikes = data.get('nbBikes', station.nbBikes)
    station.nbEBikes = data.get('nbEBikes', station.nbEBikes)
    station.nbFreeDocks = data.get('nbFreeDocks', station.nbFreeDocks)
    station.status = data.get('status', station.status)
    
    db.session.commit()
    return jsonify({'message': 'Station mise à jour avec succès'})

@app.route('/api/stations/<int:id>', methods=['DELETE'])
@token_required
def delete_station(current_user, id):
    station = Station.query.get_or_404(id)
    db.session.delete(station)
    db.session.commit()
    return jsonify({'message': 'Station supprimée avec succès'})

# ==================== IMPORT CSV ====================
def import_csv():
    """Importe les données du CSV dans la base de données"""
    if Station.query.count() > 0:
        print("✅ Données déjà importées")
        return
    
    try:
        # Lecture du CSV sans header (ton CSV n'a pas de ligne d'en-tête)
        df = pd.read_csv('velib-pos.csv', sep=';', header=None)
        
        print(f"📊 {len(df)} lignes trouvées dans le CSV")
        
        imported = 0
        errors = 0
        
        for index, row in df.iterrows():
            try:
                # La colonne 6 contient le JSON avec les infos de la station
                json_data = row[6]
                
                # Parse le JSON
                station_info = json.loads(json_data)
                
                # Extraction des données
                code = station_info.get('code', '')
                name = station_info.get('name', '')
                gps = station_info.get('gps', {})
                latitude = gps.get('latitude', 0)
                longitude = gps.get('longitude', 0)
                status = station_info.get('state', 'Operative')
                
                # Extraction des autres colonnes numériques
                nbBikes = int(row[0]) if pd.notna(row[0]) else 0
                nbEBikes = int(row[2]) if pd.notna(row[2]) else 0
                nbFreeDocks = int(row[9]) if pd.notna(row[9]) else 0
                
                # Vérifier que les données sont valides
                if not code or latitude == 0 or longitude == 0:
                    continue
                
                # Créer la station
                station = Station(
                    code=code,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    nbBikes=nbBikes,
                    nbEBikes=nbEBikes,
                    nbFreeDocks=nbFreeDocks,
                    status=status
                )
                
                db.session.add(station)
                imported += 1
                
            except Exception as e:
                errors += 1
                if errors < 5:  # Afficher seulement les 5 premières erreurs
                    print(f"⚠️ Erreur ligne {index}: {str(e)}")
                continue
        
        db.session.commit()
        print(f"✅ {imported} stations importées avec succès")
        if errors > 0:
            print(f"⚠️ {errors} lignes ignorées (données invalides)")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'import du CSV : {e}")
        import traceback
        traceback.print_exc()

# ==================== MAIN ====================
if __name__ == '__main__':
    with app.app_context():
        # Créer les tables
        db.create_all()
        
        # Créer un utilisateur de test
        if User.query.count() == 0:
            test_user = User(
                username='admin',
                password=generate_password_hash('admin123')
            )
            db.session.add(test_user)
            db.session.commit()
            print("👤 Utilisateur de test créé: admin / admin123")
        
        # Importer le CSV
        import_csv()
    
    print("\n🚀 Backend Vélib démarré sur http://localhost:5000")
    print("📍 Endpoints disponibles:")
    print("   POST /api/register")
    print("   POST /api/login")
    print("   GET  /api/stations")
    print("   POST /api/stations")
    print("   PUT  /api/stations/<id>")
    print("   DELETE /api/stations/<id>\n")
    
    app.run(debug=True, port=5000)