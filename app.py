from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///betting_app.db')
# For now, use SQLite to avoid PostgreSQL issues
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///betting_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Create database tables
with app.app_context():
    db.create_all()

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

# Matka Game Models
class MatkaMarket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Kalyan, Milan Day, etc.
    open_time = db.Column(db.String(10), nullable=False)  # "09:30"
    close_time = db.Column(db.String(10), nullable=False)  # "11:30"
    is_active = db.Column(db.Boolean, default=True)
    result_time = db.Column(db.String(10), nullable=False)  # "11:35"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'open_time': self.open_time,
            'close_time': self.close_time,
            'result_time': self.result_time,
            'is_active': self.is_active,
            'status': self.get_current_status()
        }
    
    def get_current_status(self):
        from datetime import datetime
        now = datetime.now().time()
        open_time = datetime.strptime(self.open_time, "%H:%M").time()
        close_time = datetime.strptime(self.close_time, "%H:%M").time()
        
        if now < open_time:
            return 'not_started'
        elif open_time <= now < close_time:
            return 'open'
        else:
            return 'closed'

class MatkaResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('matka_market.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    open_pana = db.Column(db.String(3))  # "123"
    close_pana = db.Column(db.String(3))  # "456"
    open_ank = db.Column(db.Integer)  # 6 (1+2+3)
    close_ank = db.Column(db.Integer)  # 6 (4+5+6) 
    jodi = db.Column(db.String(2))  # "66"
    declared_at = db.Column(db.DateTime)
    is_declared = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'market_id': self.market_id,
            'date': self.date.isoformat(),
            'open_pana': self.open_pana,
            'close_pana': self.close_pana,
            'open_ank': self.open_ank,
            'close_ank': self.close_ank,
            'jodi': self.jodi,
            'is_declared': self.is_declared,
            'declared_at': self.declared_at.isoformat() if self.declared_at else None
        }

class MatkaBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    market_id = db.Column(db.Integer, db.ForeignKey('matka_market.id'), nullable=False)
    bet_type = db.Column(db.String(20), nullable=False)  # single, jodi, panna, sangam
    numbers = db.Column(db.String(100), nullable=False)  # "1,2,3" or "12,23,34"
    amount = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)  # Payout rate (9.5 for single, 95 for jodi)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(10), nullable=False)  # 'open' or 'close'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'won', 'lost'
    win_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'market_id': self.market_id,
            'bet_type': self.bet_type,
            'numbers': self.numbers,
            'amount': self.amount,
            'rate': self.rate,
            'date': self.date.isoformat(),
            'session': self.session,
            'status': self.status,
            'win_amount': self.win_amount,
            'created_at': self.created_at.isoformat()
        }

# Authentication Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate input
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
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        if user and user.check_password(data['password']):
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Dashboard Routes
@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get recent matka bets
        recent_bets = MatkaBet.query.filter_by(user_id=user_id).order_by(MatkaBet.created_at.desc()).limit(10).all()
        
        # Get active matka markets
        active_markets = MatkaMarket.query.filter_by(is_active=True).all()
        
        # Get today's results
        from datetime import date
        today_results = MatkaResult.query.filter_by(date=date.today()).all()
        
        return jsonify({
            'user': user.to_dict(),
            'recent_bets': [bet.to_dict() for bet in recent_bets],
            'active_markets': [market.to_dict() for market in active_markets],
            'today_results': [result.to_dict() for result in today_results]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Matka API Routes
@app.route('/api/matka/markets', methods=['GET'])
@jwt_required()
def get_matka_markets():
    try:
        markets = MatkaMarket.query.filter_by(is_active=True).all()
        return jsonify({
            'markets': [market.to_dict() for market in markets]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/place_bet', methods=['POST'])
@jwt_required()
def place_matka_bet():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        market_id = data.get('market_id')
        bet_type = data.get('bet_type')  # single, jodi, panna, sangam
        numbers = data.get('numbers')  # "1,2,3" or "12,23"
        amount = float(data.get('amount', 0))
        session = data.get('session', 'open')  # open or close
        
        if amount <= 0:
            return jsonify({'error': 'Invalid bet amount'}), 400
        
        if amount > user.balance:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Get rates based on bet type
        rates = {
            'single': 9.5,
            'jodi': 95.0,
            'single_panna': 142.0,
            'double_panna': 285.0,
            'triple_panna': 950.0,
            'half_sangam': 1425.0,
            'full_sangam': 9500.0
        }
        
        rate = rates.get(bet_type, 9.5)
        
        # Create new bet
        from datetime import date
        new_bet = MatkaBet(
            user_id=user_id,
            market_id=market_id,
            bet_type=bet_type,
            numbers=numbers,
            amount=amount,
            rate=rate,
            date=date.today(),
            session=session
        )
        
        # Deduct amount from user balance
        user.balance -= amount
        
        db.session.add(new_bet)
        db.session.commit()
        
        return jsonify({
            'message': 'Bet placed successfully',
            'bet': new_bet.to_dict(),
            'new_balance': user.balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/results/<int:market_id>', methods=['GET'])
@jwt_required()
def get_matka_results(market_id):
    try:
        # Get last 10 results for the market
        results = MatkaResult.query.filter_by(market_id=market_id).order_by(MatkaResult.date.desc()).limit(10).all()
        
        return jsonify({
            'results': [result.to_dict() for result in results]
        }, 200)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matka/declare_result', methods=['POST'])
def declare_matka_result():
    try:
        data = request.get_json()
        
        market_id = data.get('market_id')
        open_pana = data.get('open_pana')
        close_pana = data.get('close_pana')
        result_date = data.get('date')
        
        from datetime import datetime
        date_obj = datetime.strptime(result_date, '%Y-%m-%d').date()
        
        # Calculate anks and jodi
        open_ank = sum(int(d) for d in open_pana) % 10
        close_ank = sum(int(d) for d in close_pana) % 10
        jodi = f"{open_ank}{close_ank}"
        
        # Check if result already exists
        existing_result = MatkaResult.query.filter_by(market_id=market_id, date=date_obj).first()
        
        if existing_result:
            # Update existing result
            existing_result.open_pana = open_pana
            existing_result.close_pana = close_pana
            existing_result.open_ank = open_ank
            existing_result.close_ank = close_ank
            existing_result.jodi = jodi
            existing_result.is_declared = True
            existing_result.declared_at = datetime.utcnow()
        else:
            # Create new result
            new_result = MatkaResult(
                market_id=market_id,
                date=date_obj,
                open_pana=open_pana,
                close_pana=close_pana,
                open_ank=open_ank,
                close_ank=close_ank,
                jodi=jodi,
                is_declared=True,
                declared_at=datetime.utcnow()
            )
            db.session.add(new_result)
        
        # Process winning bets
        _process_winning_bets(market_id, date_obj, open_pana, close_pana, open_ank, close_ank, jodi)
        
        db.session.commit()
        
        return jsonify({'message': 'Result declared successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _process_winning_bets(market_id, date_obj, open_pana, close_pana, open_ank, close_ank, jodi):
    """Process and update winning bets"""
    bets = MatkaBet.query.filter_by(market_id=market_id, date=date_obj, status='pending').all()
    
    for bet in bets:
        is_winner = False
        
        if bet.bet_type == 'single':
            # Check if bet number matches open or close ank
            bet_numbers = bet.numbers.split(',')
            if bet.session == 'open' and str(open_ank) in bet_numbers:
                is_winner = True
            elif bet.session == 'close' and str(close_ank) in bet_numbers:
                is_winner = True
        
        elif bet.bet_type == 'jodi':
            if bet.numbers == jodi:
                is_winner = True
        
        elif bet.bet_type == 'single_panna':
            if bet.session == 'open' and bet.numbers == open_pana:
                is_winner = True
            elif bet.session == 'close' and bet.numbers == close_pana:
                is_winner = True
        
        if is_winner:
            bet.status = 'won'
            bet.win_amount = bet.amount * bet.rate
            
            # Add winnings to user balance
            user = User.query.get(bet.user_id)
            user.balance += bet.win_amount
        else:
            bet.status = 'lost'

@app.route('/api/place_bet', methods=['POST'])
@jwt_required()
def place_bet():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        bet_amount = float(data.get('amount', 0))
        if bet_amount <= 0:
            return jsonify({'error': 'Invalid bet amount'}), 400
        
        if bet_amount > user.balance:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Create new bet
        new_bet = BetHistory(
            user_id=user_id,
            match_name=data.get('match_name', ''),
            bet_amount=bet_amount,
            bet_type=data.get('bet_type', ''),
            odds=float(data.get('odds', 1.0))
        )
        
        # Deduct amount from user balance
        user.balance -= bet_amount
        
        db.session.add(new_bet)
        db.session.commit()
        
        return jsonify({
            'message': 'Bet placed successfully',
            'bet': new_bet.to_dict(),
            'new_balance': user.balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Betting API is running'}), 200

@app.route('/api/matka/live-data', methods=['GET'])
def get_live_data():
    try:
        import random
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

@app.route('/api/matka/results', methods=['GET'])
def get_matka_results_today():
    try:
        from datetime import date
        today_results = MatkaResult.query.filter_by(date=date.today()).all()
        
        return jsonify({
            'results': [result.to_dict() for result in today_results]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Add default Matka markets if they don't exist
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
            print("Default Matka markets added successfully!")
        
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)