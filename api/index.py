from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/betting_app.db'  # Use /tmp for serverless
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, 
     origins=['*'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# Add preflight handler for OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=1000.0)  # Starting balance
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

class BetHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_name = db.Column(db.String(200), nullable=False)
    bet_amount = db.Column(db.Float, nullable=False)
    bet_type = db.Column(db.String(50), nullable=False)  # 'win', 'lose', 'draw'
    odds = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'won', 'lost'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('bets', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_name': self.match_name,
            'bet_amount': self.bet_amount,
            'bet_type': self.bet_type,
            'odds': self.odds,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class MatkaMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    open_time = db.Column(db.String(10), nullable=False)  # Format: "HH:MM"
    close_time = db.Column(db.String(10), nullable=False)
    result_time = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'open_time': self.open_time,
            'close_time': self.close_time,
            'result_time': self.result_time,
            'is_active': self.is_active
        }

# Create tables on startup (for serverless)
def init_db():
    try:
        with app.app_context():
            db.create_all()
            
            # Add default markets if they don't exist
            if MatkaMarket.query.count() == 0:
                markets = [
                    MatkaMarket(name='Kalyan', open_time='15:45', close_time='16:45', result_time='16:50'),
                    MatkaMarket(name='Milan Day', open_time='09:30', close_time='10:30', result_time='10:35'),
                    MatkaMarket(name='Milan Night', open_time='21:30', close_time='22:30', result_time='22:35'),
                    MatkaMarket(name='Rajdhani Day', open_time='13:40', close_time='14:40', result_time='14:45'),
                    MatkaMarket(name='Rajdhani Night', open_time='19:40', close_time='20:40', result_time='20:45'),
                    MatkaMarket(name='Time Bazar', open_time='10:30', close_time='11:30', result_time='11:35'),
                    MatkaMarket(name='Sridevi', open_time='11:30', close_time='12:30', result_time='12:35'),
                    MatkaMarket(name='Sridevi Night', open_time='20:30', close_time='21:30', result_time='21:35')
                ]
                
                for market in markets:
                    db.session.add(market)
                
                db.session.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database
init_db()

# Routes
@app.route('/')
def home():
    return jsonify({'message': 'Betting API is running', 'status': 'success'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'Betting API is running on Vercel'})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validation
        if not data or not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
            
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create access token
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
        
        # Find user
        user = User.query.filter_by(username=data['username']).first()
        
        if user and user.check_password(data['password']):
            # Create access token
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
        
        # Get recent bets
        recent_bets = BetHistory.query.filter_by(user_id=current_user_id)\
                                     .order_by(BetHistory.created_at.desc())\
                                     .limit(10).all()
        
        # Get available markets
        markets = MatkaMarket.query.filter_by(is_active=True).all()
        
        return jsonify({
            'user': user.to_dict(),
            'recent_bets': [bet.to_dict() for bet in recent_bets],
            'available_matches': [market.to_dict() for market in markets]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_bet', methods=['POST'])
@jwt_required()
def place_bet():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or not all(k in data for k in ['match_name', 'amount', 'bet_type', 'odds']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        bet_amount = float(data['amount'])
        
        # Check if user has sufficient balance
        if user.balance < bet_amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Create bet record
        bet = BetHistory(
            user_id=current_user_id,
            match_name=data['match_name'],
            bet_amount=bet_amount,
            bet_type=data['bet_type'],
            odds=float(data['odds'])
        )
        
        # Deduct amount from user balance
        user.balance -= bet_amount
        
        db.session.add(bet)
        db.session.commit()
        
        return jsonify({
            'message': 'Bet placed successfully',
            'bet': bet.to_dict(),
            'new_balance': user.balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For Vercel serverless deployment
def handler(environ, start_response):
    return app(environ, start_response)

# Vercel entry point
application = app

if __name__ == '__main__':
    app.run(debug=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=1000.0)  # Starting balance
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

class BetHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_name = db.Column(db.String(200), nullable=False)
    bet_amount = db.Column(db.Float, nullable=False)
    bet_type = db.Column(db.String(50), nullable=False)  # 'win', 'lose', 'draw'
    odds = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'won', 'lost'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('bets', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_name': self.match_name,
            'bet_amount': self.bet_amount,
            'bet_type': self.bet_type,
            'odds': self.odds,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class MatkaMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    open_time = db.Column(db.String(10), nullable=False)  # Format: "HH:MM"
    close_time = db.Column(db.String(10), nullable=False)
    result_time = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'open_time': self.open_time,
            'close_time': self.close_time,
            'result_time': self.result_time,
            'is_active': self.is_active
        }

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validation
        if not data or not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
            
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create access token
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
        
        # Find user
        user = User.query.filter_by(username=data['username']).first()
        
        if user and user.check_password(data['password']):
            # Create access token
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
        
        # Get recent bets
        recent_bets = BetHistory.query.filter_by(user_id=current_user_id)\
                                     .order_by(BetHistory.created_at.desc())\
                                     .limit(10).all()
        
        # Get available markets
        markets = MatkaMarket.query.filter_by(is_active=True).all()
        
        return jsonify({
            'user': user.to_dict(),
            'recent_bets': [bet.to_dict() for bet in recent_bets],
            'available_matches': [market.to_dict() for market in markets]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_bet', methods=['POST'])
@jwt_required()
def place_bet():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or not all(k in data for k in ['match_name', 'amount', 'bet_type', 'odds']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        bet_amount = float(data['amount'])
        
        # Check if user has sufficient balance
        if user.balance < bet_amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Create bet record
        bet = BetHistory(
            user_id=current_user_id,
            match_name=data['match_name'],
            bet_amount=bet_amount,
            bet_type=data['bet_type'],
            odds=float(data['odds'])
        )
        
        # Deduct amount from user balance
        user.balance -= bet_amount
        
        db.session.add(bet)
        db.session.commit()
        
        return jsonify({
            'message': 'Bet placed successfully',
            'bet': bet.to_dict(),
            'new_balance': user.balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Betting API is running'}), 200

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()
        
        # Add default markets if they don't exist
        if MatkaMarket.query.count() == 0:
            markets = [
                MatkaMarket(name='Kalyan', open_time='15:45', close_time='16:45', result_time='16:50'),
                MatkaMarket(name='Milan Day', open_time='09:30', close_time='10:30', result_time='10:35'),
                MatkaMarket(name='Milan Night', open_time='21:30', close_time='22:30', result_time='22:35'),
                MatkaMarket(name='Rajdhani Day', open_time='13:40', close_time='14:40', result_time='14:45'),
                MatkaMarket(name='Rajdhani Night', open_time='19:40', close_time='20:40', result_time='20:45'),
                MatkaMarket(name='Time Bazar', open_time='10:30', close_time='11:30', result_time='11:35'),
                MatkaMarket(name='Sridevi', open_time='11:30', close_time='12:30', result_time='12:35'),
                MatkaMarket(name='Sridevi Night', open_time='20:30', close_time='21:30', result_time='21:35')
            ]
            
            for market in markets:
                db.session.add(market)
            
            db.session.commit()

# Create tables on startup
create_tables()

# Vercel handler
app = app