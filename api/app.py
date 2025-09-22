from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

# Flask app setup for serverless
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Use in-memory SQLite for serverless environment
if os.environ.get('VERCEL_ENV'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("betting_app.db")}')
    
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# CORS configuration for Vercel
CORS(app, origins=['*'], methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], 
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'])

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BetHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_name = db.Column(db.String(200), nullable=False)
    bet_amount = db.Column(db.Float, nullable=False)
    bet_type = db.Column(db.String(50), nullable=False)
    odds = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MatkaMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    open_time = db.Column(db.String(10), nullable=False)
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

# Initialize database on app startup
with app.app_context():
    try:
        db.create_all()
        print(f"Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Create default admin user if no users exist
        user_count = User.query.count()
        print(f"Current user count: {user_count}")
        
        if user_count == 0:
            admin_user = User(username='admin', email='admin@example.com')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            
            # Create test user
            test_user = User(username='test', email='test@example.com')
            test_user.set_password('test123')
            db.session.add(test_user)
            
            db.session.commit()
            print("Created default users: admin/admin123 and test/test123")
            
            # Verify users were created
            user_count_after = User.query.count()
            print(f"User count after creation: {user_count_after}")
        else:
            print("Users already exist in database")
            # Print existing users
            users = User.query.all()
            for user in users:
                print(f"Existing user: {user.username}")
        
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
            print("Created default markets")
    except Exception as e:
        print(f"Database init error: {e}")
        import traceback
        traceback.print_exc()

# Routes
@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Betting API is running on Vercel', 'status': 'success'})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'message': 'Betting API is running on Vercel'})

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
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

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
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

@app.route('/api/dashboard', methods=['GET', 'OPTIONS'])
@jwt_required()
def dashboard():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        recent_bets = BetHistory.query.filter_by(user_id=current_user_id)\
                                     .order_by(BetHistory.created_at.desc())\
                                     .limit(10).all()
        
        markets = MatkaMarket.query.filter_by(is_active=True).all()
        
        return jsonify({
            'user': user.to_dict(),
            'recent_bets': [bet.to_dict() for bet in recent_bets],
            'available_matches': [market.to_dict() for market in markets]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_bet', methods=['POST', 'OPTIONS'])
@jwt_required()
def place_bet():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or not all(k in data for k in ['match_name', 'amount', 'bet_type', 'odds']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        bet_amount = float(data['amount'])
        
        if user.balance < bet_amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        bet = BetHistory(
            user_id=current_user_id,
            match_name=data['match_name'],
            bet_amount=bet_amount,
            bet_type=data['bet_type'],
            odds=float(data['odds'])
        )
        
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

@app.route('/api/matka/markets', methods=['GET', 'OPTIONS'])
def get_matka_markets():
    """Get real-time Matka market data"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        import random
        from datetime import datetime, timedelta
        
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        markets = [
            {
                'id': 1,
                'name': 'KALYAN',
                'openTime': '15:45',
                'closeTime': '16:45',
                'resultTime': '16:50',
                'icon': '🏆',
                'color': '#4CAF50',
                'players': random.randint(2000, 3000),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 16 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 2,
                'name': 'MILAN DAY',
                'openTime': '10:30',
                'closeTime': '11:30',
                'resultTime': '11:35',
                'icon': '💎',
                'color': '#2196F3',
                'players': random.randint(1500, 2500),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 11 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 3,
                'name': 'MILAN NIGHT',
                'openTime': '21:30',
                'closeTime': '22:30',
                'resultTime': '22:35',
                'icon': '🌙',
                'color': '#9C27B0',
                'players': random.randint(2500, 4000),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 22 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 4,
                'name': 'RAJDHANI DAY',
                'openTime': '13:40',
                'closeTime': '14:40',
                'resultTime': '14:45',
                'icon': '👑',
                'color': '#FF9800',
                'players': random.randint(1200, 2000),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 14 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 5,
                'name': 'RAJDHANI NIGHT',
                'openTime': '19:40',
                'closeTime': '20:40',
                'resultTime': '20:45',
                'icon': '🌟',
                'color': '#E91E63',
                'players': random.randint(2000, 3500),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 20 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 6,
                'name': 'TIME BAZAR',
                'openTime': '10:30',
                'closeTime': '11:30',
                'resultTime': '11:35',
                'icon': '⏰',
                'color': '#607D8B',
                'players': random.randint(1000, 1800),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 11 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 7,
                'name': 'MADHUR DAY',
                'openTime': '12:00',
                'closeTime': '13:00',
                'resultTime': '13:05',
                'icon': '🍯',
                'color': '#FF5722',
                'players': random.randint(1500, 2300),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 13 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            },
            {
                'id': 8,
                'name': 'MADHUR NIGHT',
                'openTime': '20:55',
                'closeTime': '21:55',
                'resultTime': '22:00',
                'icon': '🌃',
                'color': '#795548',
                'players': random.randint(1800, 2800),
                'todayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}' if now.hour >= 22 else 'XXX-XX',
                'yesterdayResult': f'{random.randint(100, 999)}-{random.randint(10, 99)}'
            }
        ]
        
        # Update market status based on current time
        for market in markets:
            open_time = datetime.strptime(market['openTime'], '%H:%M').time()
            close_time = datetime.strptime(market['closeTime'], '%H:%M').time()
            result_time = datetime.strptime(market['resultTime'], '%H:%M').time()
            current = now.time()
            
            if open_time <= current <= close_time:
                market['status'] = 'OPEN'
            elif close_time < current <= result_time:
                market['status'] = 'RUNNING'
            else:
                market['status'] = 'CLOSED'
        
        return jsonify({'markets': markets}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/results', methods=['GET', 'OPTIONS'])
def get_matka_results():
    """Get today's Matka results"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        import random
        from datetime import datetime
        
        now = datetime.now()
        
        results = []
        markets = ['KALYAN', 'MILAN DAY', 'MILAN NIGHT', 'RAJDHANI DAY', 'RAJDHANI NIGHT', 'TIME BAZAR', 'MADHUR DAY', 'MADHUR NIGHT']
        icons = ['🏆', '💎', '🌙', '👑', '🌟', '⏰', '🍯', '🌃']
        times = ['16:50', '11:35', '22:35', '14:45', '20:45', '11:35', '13:05', '22:00']
        
        for i, market in enumerate(markets):
            # Show result only if time has passed
            result_hour = int(times[i].split(':')[0])
            if now.hour >= result_hour:
                results.append({
                    'market': market,
                    'result': f'{random.randint(100, 999)}-{random.randint(10, 99)}',
                    'time': times[i],
                    'icon': icons[i]
                })
        
        return jsonify({'results': results[:3]}), 200  # Return only top 3 recent results
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/live-data', methods=['GET', 'OPTIONS'])
def get_live_data():
    """Get live Matka data including player counts and betting volume"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        import random
        
        live_data = {
            'totalPlayers': random.randint(15000, 25000),
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

# Initialize database and default data
def init_db():
    """Initialize database and create default data"""
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

# Initialize database when app starts
with app.app_context():
    init_db()

# For local testing
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)