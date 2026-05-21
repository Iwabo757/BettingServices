from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SECRET_KEY'] = 'supersecretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.ebxdbkmnchebkbhihebr:C7SryYAIB9Lpo4rN@aws-1-us-east-1.pooler.supabase.com:6543/postgres'

# DATABASE

db = SQLAlchemy(app)

# MODELS

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    profit = db.Column(db.Float, default=0)

    bets_won = db.Column(db.Integer, default=0)

    bets_lost = db.Column(db.Integer, default=0)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    player = db.Column(db.String(100))
    target_encounter = db.Column(db.Integer)
    current_encounter = db.Column(db.Integer, default=0)
    actual_encounter = db.Column(db.Integer, nullable=True)
    bet_amount = db.Column(db.Float, default=0)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Open')
    payout = db.Column(db.Integer, default=0)

class SubBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer)
    label = db.Column(db.String(100))
    odds = db.Column(db.Float)

# ROUTES

@app.route('/')
def home():
    bets = Bet.query.filter_by(status='Open').all()

    return render_template(
        'home.html',
        bets=bets
    )

@app.route('/bets')
def bets():
    bets = Bet.query.filter_by(status='Open').all()

    return render_template(
        'index.html',
        bets=bets
    )

@app.route('/history')
def history():
    bets = Bet.query.filter(
        Bet.status.in_(['Won', 'Lost'])
    ).all()

    return render_template(
        'history.html',
        bets=bets
    )

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'fate123':

            session['admin'] = True

            return redirect(url_for('admin'))

        return 'Invalid Login'

    return render_template('login.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

@app.route('/leaderboard')
def leaderboard():

    users = User.query.order_by(User.profit.desc()).all()

    return render_template(
        'leaderboard.html',
        users=users
    )

@app.route('/analytics')
def analytics():

    total_wins = Bet.query.filter_by(status='Won').count()

    total_losses = Bet.query.filter_by(status='Lost').count()

    total_bet_amount = db.session.query(
        db.func.sum(Bet.bet_amount)
    ).scalar() or 0

    total_payouts = db.session.query(
        db.func.sum(Bet.payout)
    ).scalar() or 0

    house_profit = int(
        total_bet_amount - total_payouts
    )

    return render_template(
        'analytics.html',
        wins=total_wins,
        losses=total_losses,
        house_profit=house_profit,
        total_bets=total_bet_amount,
        total_payouts=total_payouts
    )

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if not session.get('admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':

        pokemon = request.form['pokemon']
        player = request.form['player']
        target = request.form['target']
        current = request.form['current']
        amount = request.form['amount']
        description = request.form['description']

        bet = Bet(
            title=pokemon,
            player=player,
            target_encounter=target,
            current_encounter=current,
            bet_amount=amount,
            description=description
        )

        db.session.add(bet)
        db.session.commit()

        return redirect(url_for('admin'))

    bets = Bet.query.all()

    return render_template(
        'admin.html',
        bets=bets
    )

@app.route('/settle/<int:bet_id>', methods=['POST'])
def settle_bet(bet_id):

    bet = Bet.query.get_or_404(bet_id)

    actual = int(request.form['actual_encounter'])

    bet.actual_encounter = actual

    difference = abs(
    actual - bet.target_encounter
    )

    multiplier = 1.0

    if difference <= 10:
        multiplier = 3.0

    elif difference <= 50:
        multiplier = 2.5

    elif difference <= 100:
        multiplier = 2.0

    elif difference <= 250:
        multiplier = 1.75

    elif difference <= 500:
        multiplier = 1.5

    elif difference <= 1000:
        multiplier = 1.25

    elif difference <= 2000:
        multiplier = 1.20

    elif difference <= 3000:
        multiplier = 1.15

    elif difference <= 4000:
        multiplier = 1.10

    else:
        multiplier = 1.0

    gross_payout = int(
    bet.bet_amount * multiplier
    )

    house_cut = int(
        gross_payout * 0.10
    )

    final_payout = gross_payout - house_cut

    bet.payout = final_payout

    user = User.query.filter_by(
        username=bet.player
    ).first()

    if not user:

        user = User(
            username=bet.player,
            profit=0,
            bets_won=0,
            bets_lost=0
        )

        db.session.add(user)

    if user.profit is None:
        user.profit = 0

    if user.bets_won is None:
        user.bets_won = 0

    if user.bets_lost is None:
        user.bets_lost = 0

    if multiplier > 1.0:

        bet.status = 'Won'

        user.bets_won += 1

        user.profit += final_payout

    else:

        bet.status = 'Lost'

        user.bets_lost += 1

        user.profit -= int(bet.bet_amount)

    db.session.commit()

    return redirect(url_for('admin'))

@app.route('/delete_bet/<int:bet_id>', methods=['POST'])
def delete_bet(bet_id):

    if not session.get('admin'):
        return redirect(url_for('login'))

    bet = Bet.query.get_or_404(bet_id)

    db.session.delete(bet)

    db.session.commit()

    return redirect(url_for('history'))
# START APP

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)