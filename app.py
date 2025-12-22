from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timezone, timedelta
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'strive_v10_final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///strive.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

NINJA_API_KEY = os.environ.get('NINJA_API_KEY', 'leUU4Ev+HdzK9FttH+zoqw==APuke9X3X0HHqY9k')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    logs = db.relationship('DailyLog', backref='author', lazy=True)
    templates = db.relationship('DietTemplate', backref='owner', lazy=True)

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Integer, default=0)
    steps = db.Column(db.Integer, default=0)
    workout = db.Column(db.String(100))
    intensity = db.Column(db.Integer, default=0)
    water = db.Column(db.Float, default=0.0)
    sleep = db.Column(db.Float, default=0.0) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cheers = db.relationship('Cheer', backref='log', lazy=True)

class DietTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer)
    protein = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Cheer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    log_id = db.Column(db.Integer, db.ForeignKey('daily_log.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---
@app.route("/")
@login_required
def home():
    if 'food_log' not in session:
        session['food_log'] = []
    totals = {"cal": sum(f['c'] for f in session['food_log']), "pro": round(sum(f['p'] for f in session['food_log']), 1)}
    user_templates = DietTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", food_log=session['food_log'], totals=totals, templates=user_templates)

@app.route("/add_food", methods=["POST"])
@login_required
def add_food():
    template_id = request.form.get("template_id")
    if template_id:
        t = DietTemplate.query.get(template_id)
        name, cals, pros = t.name, t.calories, t.protein
    else:
        query = request.form.get("name")
        api_url = f'https://api.calorieninjas.com/v1/nutrition?query={query}'
        res = requests.get(api_url, headers={'X-Api-Key': NINJA_API_KEY})
        if res.status_code == 200 and res.json()['items']:
            data = res.json()['items']
            cals, pros, name = sum(i['calories'] for i in data), sum(i['protein_g'] for i in data), query
        else:
            return redirect(url_for('home'))
    temp = session.get('food_log', []); temp.append({"n": name, "c": int(cals), "p": round(pros, 1)})
    session['food_log'] = temp; session.modified = True
    return redirect(url_for('home'))

@app.route("/delete_food/<int:index>")
@login_required
def delete_food(index):
    temp = session.get('food_log', [])
    if 0 <= index < len(temp): temp.pop(index); session['food_log'] = temp; session.modified = True
    return redirect(url_for('home'))

@app.route("/save_template", methods=["POST"])
@login_required
def save_template():
    name = request.form.get("t_name")
    cal_r, pro_r = request.form.get("t_cal"), request.form.get("t_pro")
    if not cal_r or not pro_r:
        res = requests.get(f'https://api.calorieninjas.com/v1/nutrition?query={name}', headers={'X-Api-Key': NINJA_API_KEY})
        if res.status_code == 200 and res.json()['items']:
            items = res.json()['items']
            cal, pro = int(sum(i['calories'] for i in items)), int(sum(i['protein_g'] for i in items))
        else: return redirect(url_for('home'))
    else: cal, pro = int(cal_r), int(pro_r)
    db.session.add(DietTemplate(name=name, calories=cal, protein=pro, user_id=current_user.id))
    db.session.commit(); return redirect(url_for('home'))

@app.route("/finish_day", methods=["POST"])
@login_required
def finish_day():
    new_log = DailyLog(
        calories=sum(f['c'] for f in session.get('food_log', [])),
        protein=sum(f['p'] for f in session.get('food_log', [])),
        steps=int(request.form.get('steps') or 0),
        workout=request.form.get('workout') or 'Active',
        intensity=int(request.form.get('intensity') or 5),
        water=float(request.form.get('final_water') or 0.0),
        sleep=float(request.form.get('sleep') or 7.5),
        user_id=current_user.id
    )
    db.session.add(new_log); db.session.commit(); session['food_log'] = []
    return redirect(url_for('leaderboard'))

@app.route("/leaderboard")
@login_required
def leaderboard():
    all_logs = DailyLog.query.order_by(DailyLog.date.desc()).all()
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_logs = DailyLog.query.filter(DailyLog.date >= one_week_ago).all()
    user_scores = {}
    for log in weekly_logs:
        score = (log.steps / 1000) + log.protein + (log.intensity * 10)
        user_scores[log.author.username] = user_scores.get(log.author.username, 0) + score
    winner = None
    if user_scores:
        winner_name = max(user_scores, key=user_scores.get)
        winner = {"name": winner_name, "score": round(user_scores[winner_name], 1)}
    return render_template("leaderboard.html", logs=all_logs, winner=winner)

@app.route("/history")
@login_required
def history():
    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).all()
    return render_template("history.html", logs=logs)

@app.route("/cheer/<int:log_id>", methods=["POST"])
@login_required
def cheer(log_id):
    if not Cheer.query.filter_by(user_id=current_user.id, log_id=log_id).first():
        db.session.add(Cheer(user_id=current_user.id, log_id=log_id)); db.session.commit()
    return redirect(url_for('leaderboard'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username")).first()
        if u and u.password == request.form.get("password"): login_user(u); return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = User(username=request.form.get("username"), password=request.form.get("password"))
        db.session.add(u); db.session.commit(); login_user(u); return redirect(url_for("home"))
    return render_template("signup.html")

@app.route("/logout")
def logout(): logout_user(); return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
