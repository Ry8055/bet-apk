from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import random

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'render-production-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///betting_app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-render-secret-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, origins=['*'])

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'balance': self.balance,
            'created_at': self.created_at.isoformat()
        }

# Routes
@app.route('/')
def home():
    return jsonify({'message': 'Betting API on Render!', 'status': 'success', 'platform': 'render.com'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'Betting API running on Render', 'timestamp': datetime.now().isoformat()})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
            
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(username=data['username'], email=data['email'])
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing username or password'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if user and user.check_password(data['password']):
            access_token = create_access_token(identity=user.id)
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Sample betting markets
        markets = [
            {'name': 'KALYAN', 'time': '09:30 AM', 'status': 'Open', 'result': '***-**-***'},
            {'name': 'MILAN DAY', 'time': '11:00 AM', 'status': 'Open', 'result': '***-**-***'},
            {'name': 'RAJDHANI DAY', 'time': '12:30 PM', 'status': 'Open', 'result': '***-**-***'},
            {'name': 'MAIN BAZAR', 'time': '02:00 PM', 'status': 'Open', 'result': '***-**-***'},
        ]
        
        return jsonify({
            'user': user.to_dict(),
            'markets': markets,
            'recent_bets': []
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/live-data', methods=['GET'])
def get_live_data():
    try:
        live_data = {
            'timestamp': datetime.now().isoformat(),
            'totalBetsToday': random.randint(50000, 100000),
            'activeBetting': random.randint(500, 1500),
            'lastUpdate': datetime.now().isoformat(),
            'hotMarkets': [
                {'name': 'KALYAN', 'players': random.randint(2000, 3000), 'trend': 'up'},
                {'name': 'MILAN NIGHT', 'players': random.randint(2500, 4000), 'trend': 'up'},
                {'name': 'RAJDHANI NIGHT', 'players': random.randint(2000, 3500), 'trend': 'stable'}
            ]
        }
        return jsonify(live_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database
@app.before_first_request
def create_tables():
    try:
        db.create_all()
        # Create demo user if not exists
        if not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo', email='demo@example.com')
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)