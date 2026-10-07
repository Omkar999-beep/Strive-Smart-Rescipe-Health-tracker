import os
import re
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'strive_v10_secret_fitness_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///strive.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

NINJA_API_KEY = os.environ.get('NINJA_API_KEY', '')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# --- COMMON NUTRITION DATABASE FALLBACK ---
NUTRITION_LOOKUP = {
    "egg": {"cal": 78, "pro": 6.3},
    "eggs": {"cal": 156, "pro": 12.6},
    "boiled egg": {"cal": 78, "pro": 6.3},
    "egg white": {"cal": 17, "pro": 3.6},
    "chicken breast": {"cal": 165, "pro": 31.0},
    "chicken": {"cal": 220, "pro": 26.0},
    "rice": {"cal": 130, "pro": 2.7},
    "cooked rice": {"cal": 130, "pro": 2.7},
    "brown rice": {"cal": 111, "pro": 2.6},
    "oats": {"cal": 389, "pro": 16.9},
    "oatmeal": {"cal": 150, "pro": 5.0},
    "banana": {"cal": 105, "pro": 1.3},
    "apple": {"cal": 95, "pro": 0.5},
    "whey protein": {"cal": 120, "pro": 24.0},
    "protein shake": {"cal": 160, "pro": 25.0},
    "peanut butter": {"cal": 188, "pro": 8.0},
    "milk": {"cal": 122, "pro": 8.0},
    "whole milk": {"cal": 149, "pro": 7.7},
    "almond milk": {"cal": 30, "pro": 1.0},
    "salmon": {"cal": 208, "pro": 22.0},
    "tuna": {"cal": 132, "pro": 28.0},
    "paneer": {"cal": 265, "pro": 18.0},
    "roti": {"cal": 110, "pro": 3.0},
    "chapati": {"cal": 110, "pro": 3.0},
    "bread": {"cal": 80, "pro": 3.0},
    "toast": {"cal": 80, "pro": 3.0},
    "greek yogurt": {"cal": 130, "pro": 15.0},
    "yogurt": {"cal": 100, "pro": 6.0},
    "beef": {"cal": 250, "pro": 26.0},
    "steak": {"cal": 270, "pro": 26.0},
    "avocado": {"cal": 240, "pro": 3.0},
    "almonds": {"cal": 160, "pro": 6.0},
    "pasta": {"cal": 220, "pro": 8.0},
    "salad": {"cal": 120, "pro": 3.0},
    "coffee": {"cal": 5, "pro": 0.3},
}

def lookup_nutrition(query):
    query = (query or "").strip().lower()
    if not query:
        return None
        
    # 1. Try CalorieNinjas API if key is configured
    if NINJA_API_KEY:
        try:
            api_url = f'https://api.calorieninjas.com/v1/nutrition?query={query}'
            res = requests.get(api_url, headers={'X-Api-Key': NINJA_API_KEY}, timeout=3.5)
            if res.status_code == 200:
                payload = res.json()
                items = payload.get('items', [])
                if items:
                    cals = int(sum(i.get('calories', 0) for i in items))
                    pros = round(sum(i.get('protein_g', 0) for i in items), 1)
                    return {"name": query.title(), "cals": cals, "pros": pros}
        except Exception:
            pass

    # 2. Try Local Lookup with simple quantity parsing (e.g. "2 eggs", "3 bananas")
    multiplier = 1.0
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(?:x\s*)?(.+)$", query)
    cleaned_query = query
    if match:
        multiplier = float(match.group(1))
        cleaned_query = match.group(2).strip()

    # Exact or substring match in dictionary
    for key, data in NUTRITION_LOOKUP.items():
        if key == cleaned_query or key in cleaned_query:
            cals = int(round(data["cal"] * multiplier))
            pros = round(data["pro"] * multiplier, 1)
            return {"name": query.title(), "cals": cals, "pros": pros}

    return None

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    calorie_goal = db.Column(db.Integer, default=2200)
    protein_goal = db.Column(db.Integer, default=150)
    water_goal = db.Column(db.Float, default=3.0)
    steps_goal = db.Column(db.Integer, default=10000)
    logs = db.relationship('DailyLog', backref='author', lazy=True, cascade="all, delete-orphan")
    templates = db.relationship('DietTemplate', backref='owner', lazy=True, cascade="all, delete-orphan")
    cheers = db.relationship('Cheer', backref='user', lazy=True, cascade="all, delete-orphan")

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Float, default=0.0)
    steps = db.Column(db.Integer, default=0)
    workout = db.Column(db.String(100), default="Active")
    intensity = db.Column(db.Integer, default=5)
    water = db.Column(db.Float, default=0.0)
    sleep = db.Column(db.Float, default=7.5)
    weight = db.Column(db.Float, default=70.0)
    notes = db.Column(db.String(255), default="")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cheers = db.relationship('Cheer', backref='log', lazy=True, cascade="all, delete-orphan")

class DietTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Cheer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    log_id = db.Column(db.Integer, db.ForeignKey('daily_log.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- DATABASE INITIALIZATION & SCHEMA MIGRATION ---
with app.app_context():
    db.create_all()
    # Ensure SQLite columns exist for backward compatibility
    try:
        engine = db.engine
        with engine.connect() as conn:
            from sqlalchemy import text
            # Check DailyLog columns
            daily_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(daily_log)")).fetchall()]
            if 'weight' not in daily_cols:
                conn.execute(text("ALTER TABLE daily_log ADD COLUMN weight FLOAT DEFAULT 70.0"))
            if 'notes' not in daily_cols:
                conn.execute(text("ALTER TABLE daily_log ADD COLUMN notes VARCHAR(255) DEFAULT ''"))
            
            # Check User columns
            user_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(user)")).fetchall()]
            if 'calorie_goal' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN calorie_goal INTEGER DEFAULT 2200"))
            if 'protein_goal' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN protein_goal INTEGER DEFAULT 150"))
            if 'water_goal' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN water_goal FLOAT DEFAULT 3.0"))
            if 'steps_goal' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN steps_goal INTEGER DEFAULT 10000"))
            conn.commit()
    except Exception as e:
        print(f"Schema check error: {e}")

# --- ROUTES ---
@app.route("/")
@login_required
def home():
    if 'food_log' not in session:
        session['food_log'] = []
    
    food_log = session.get('food_log', [])
    totals = {
        "cal": sum(f.get('c', 0) for f in food_log),
        "pro": round(sum(f.get('p', 0.0) for f in food_log), 1)
    }
    user_templates = DietTemplate.query.filter_by(user_id=current_user.id).all()
    
    # Check latest log to pre-fill or show status
    latest_log = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).first()
    
    return render_template(
        "index.html", 
        food_log=food_log, 
        totals=totals, 
        templates=user_templates,
        latest_log=latest_log,
        user=current_user
    )

@app.route("/add_food", methods=["POST"])
@login_required
def add_food():
    template_id = request.form.get("template_id")
    cals = 0
    pros = 0.0
    name = ""

    if template_id:
        t = db.session.get(DietTemplate, int(template_id))
        if t and t.user_id == current_user.id:
            name, cals, pros = t.name, t.calories, t.protein
            flash(f"Added {name} ({cals} kcal, {pros}g protein) from template!", "success")
        else:
            flash("Template not found.", "warning")
            return redirect(url_for('home'))
    else:
        query = request.form.get("name", "").strip()
        manual_cal = request.form.get("manual_cal")
        manual_pro = request.form.get("manual_pro")

        if not query:
            flash("Please enter a food name.", "warning")
            return redirect(url_for('home'))

        # Check manual inputs if user explicitly entered them
        if manual_cal or manual_pro:
            try:
                cals = int(manual_cal or 0)
                pros = round(float(manual_pro or 0), 1)
                name = query.title()
                flash(f"Added {name} ({cals} kcal, {pros}g protein).", "success")
            except ValueError:
                flash("Invalid numbers for calories or protein.", "danger")
                return redirect(url_for('home'))
        else:
            # Query nutrition database / API
            result = lookup_nutrition(query)
            if result:
                name = result["name"]
                cals = result["cals"]
                pros = result["pros"]
                flash(f"Added {name} ({cals} kcal, {pros}g protein).", "success")
            else:
                flash(f"Could not find nutrition data for '{query}'. Please specify calories & protein.", "warning")
                return redirect(url_for('home'))

    temp = session.get('food_log', [])
    temp.append({"n": name, "c": int(cals), "p": round(float(pros), 1)})
    session['food_log'] = temp
    session.modified = True
    return redirect(url_for('home'))

@app.route("/delete_food/<int:index>", methods=["GET", "POST"])
@login_required
def delete_food(index):
    temp = session.get('food_log', [])
    if 0 <= index < len(temp):
        removed = temp.pop(index)
        session['food_log'] = temp
        session.modified = True
        flash(f"Removed '{removed.get('n', 'item')}' from food log.", "info")
    return redirect(url_for('home'))

@app.route("/clear_food", methods=["POST"])
@login_required
def clear_food():
    session['food_log'] = []
    session.modified = True
    flash("Daily food log cleared.", "info")
    return redirect(url_for('home'))

@app.route("/save_template", methods=["POST"])
@login_required
def save_template():
    name = request.form.get("t_name", "").strip()
    cal_r = request.form.get("t_cal")
    pro_r = request.form.get("t_pro")

    if not name:
        flash("Template name is required.", "warning")
        return redirect(url_for('home'))

    if not cal_r or not pro_r:
        result = lookup_nutrition(name)
        if result:
            cal = result["cals"]
            pro = result["pros"]
        else:
            flash(f"Could not auto-lookup '{name}'. Please enter calories and protein.", "warning")
            return redirect(url_for('home'))
    else:
        try:
            cal = int(cal_r)
            pro = round(float(pro_r), 1)
        except ValueError:
            flash("Invalid numbers for template calories or protein.", "danger")
            return redirect(url_for('home'))

    new_template = DietTemplate(name=name.title(), calories=cal, protein=pro, user_id=current_user.id)
    db.session.add(new_template)
    db.session.commit()
    flash(f"Meal template '{name.title()}' saved!", "success")
    return redirect(url_for('home'))

@app.route("/delete_template/<int:template_id>", methods=["POST"])
@login_required
def delete_template(template_id):
    t = db.session.get(DietTemplate, template_id)
    if t and t.user_id == current_user.id:
        db.session.delete(t)
        db.session.commit()
        flash(f"Template '{t.name}' deleted.", "info")
    return redirect(url_for('home'))

@app.route("/finish_day", methods=["POST"])
@login_required
def finish_day():
    food_log = session.get('food_log', [])
    total_cal = sum(f.get('c', 0) for f in food_log)
    total_pro = round(sum(f.get('p', 0.0) for f in food_log), 1)

    steps = int(request.form.get('steps') or 0)
    workout = (request.form.get('workout') or 'Rest / Active Recovery').strip()
    intensity = int(request.form.get('intensity') or 5)
    water = float(request.form.get('final_water') or 0.0)
    sleep = float(request.form.get('sleep') or 7.5)
    weight = float(request.form.get('weight') or 70.0)
    notes = (request.form.get('notes') or "").strip()

    new_log = DailyLog(
        calories=total_cal,
        protein=total_pro,
        steps=steps,
        workout=workout,
        intensity=intensity,
        water=round(water, 2),
        sleep=round(sleep, 1),
        weight=round(weight, 1),
        notes=notes,
        user_id=current_user.id
    )
    db.session.add(new_log)
    db.session.commit()
    session['food_log'] = []
    session.modified = True
    flash("Awesome job! Today's log has been saved and published to the feed.", "success")
    return redirect(url_for('progress'))

@app.route("/update_goals", methods=["POST"])
@login_required
def update_goals():
    try:
        current_user.calorie_goal = int(request.form.get('calorie_goal') or 2200)
        current_user.protein_goal = int(request.form.get('protein_goal') or 150)
        current_user.steps_goal = int(request.form.get('steps_goal') or 10000)
        current_user.water_goal = float(request.form.get('water_goal') or 3.0)
        db.session.commit()
        flash("Fitness targets updated successfully!", "success")
    except Exception as e:
        flash("Could not update targets. Please check values.", "danger")
    return redirect(url_for('home'))

@app.route("/progress")
@login_required
def progress():
    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.asc()).all()
    
    # Calculate key metrics
    total_logs = len(logs)
    avg_steps = int(sum(l.steps for l in logs) / total_logs) if total_logs > 0 else 0
    avg_protein = round(sum(l.protein for l in logs) / total_logs, 1) if total_logs > 0 else 0
    avg_calories = int(sum(l.calories for l in logs) / total_logs) if total_logs > 0 else 0
    
    weights = [l.weight for l in logs if l.weight and l.weight > 0]
    current_weight = weights[-1] if weights else 70.0
    weight_change = round(weights[-1] - weights[0], 1) if len(weights) > 1 else 0.0

    return render_template(
        "progress.html",
        logs=logs,
        total_logs=total_logs,
        avg_steps=avg_steps,
        avg_protein=avg_protein,
        avg_calories=avg_calories,
        current_weight=current_weight,
        weight_change=weight_change,
        user=current_user
    )

@app.route("/training")
@login_required
def training():
    routines = [
        {
            "id": "push",
            "name": "Push Day (Chest, Shoulders, Triceps)",
            "badge": "Hypertrophy",
            "color": "#3b82f6",
            "description": "Focus on explosive chest presses, shoulder delts, and lockout triceps.",
            "exercises": [
                {"name": "Barbell Bench Press", "sets": "4 sets", "reps": "8 - 10 reps", "rest": "90s"},
                {"name": "Standing Overhead Press", "sets": "3 sets", "reps": "8 - 12 reps", "rest": "90s"},
                {"name": "Incline Dumbbell Flyes", "sets": "3 sets", "reps": "12 - 15 reps", "rest": "60s"},
                {"name": "Cable Lateral Raises", "sets": "4 sets", "reps": "15 reps", "rest": "45s"},
                {"name": "Overhead Tricep Rope Extensions", "sets": "3 sets", "reps": "12 reps", "rest": "60s"}
            ]
        },
        {
            "id": "pull",
            "name": "Pull Day (Back, Traps, Biceps)",
            "badge": "Strength & Width",
            "color": "#10b981",
            "description": "Develop full posterior chain density, lat width, and arm peak.",
            "exercises": [
                {"name": "Conventional Deadlifts", "sets": "3 sets", "reps": "5 reps", "rest": "120s"},
                {"name": "Wide Grip Lat Pulldowns", "sets": "4 sets", "reps": "10 - 12 reps", "rest": "60s"},
                {"name": "Seated Cable Rows", "sets": "3 sets", "reps": "10 - 12 reps", "rest": "60s"},
                {"name": "Face Pulls (Rear Delts)", "sets": "4 sets", "reps": "15 reps", "rest": "45s"},
                {"name": "Incline Dumbbell Bicep Curls", "sets": "3 sets", "reps": "12 reps", "rest": "60s"}
            ]
        },
        {
            "id": "legs",
            "name": "Leg Day (Quads, Hamstrings, Calves)",
            "badge": "Power & Lower Body",
            "color": "#f59e0b",
            "description": "High volume leg workout for maximum athletic power and quad growth.",
            "exercises": [
                {"name": "Barbell Back Squats", "sets": "4 sets", "reps": "6 - 8 reps", "rest": "120s"},
                {"name": "Romanian Deadlifts (RDL)", "sets": "3 sets", "reps": "8 - 10 reps", "rest": "90s"},
                {"name": "Leg Press", "sets": "3 sets", "reps": "12 - 15 reps", "rest": "90s"},
                {"name": "Lying Hamstring Leg Curls", "sets": "3 sets", "reps": "15 reps", "rest": "60s"},
                {"name": "Standing Calf Raises", "sets": "4 sets", "reps": "20 reps", "rest": "45s"}
            ]
        },
        {
            "id": "hiit",
            "name": "HIIT & Core Conditioning",
            "badge": "Endurance & Fat Burn",
            "color": "#ec4899",
            "description": "High-octane metabolic workout designed to ramp heart rate and burn calories.",
            "exercises": [
                {"name": "Kettlebell Swings", "sets": "4 sets", "reps": "20 reps", "rest": "45s"},
                {"name": "Rowing Machine Intervals", "sets": "5 sets", "reps": "250m Sprint", "rest": "60s"},
                {"name": "Box Jumps", "sets": "4 sets", "reps": "12 reps", "rest": "45s"},
                {"name": "Hanging Leg Raises", "sets": "3 sets", "reps": "15 reps", "rest": "45s"},
                {"name": "Plank with Shoulder Taps", "sets": "3 sets", "reps": "60s hold", "rest": "30s"}
            ]
        }
    ]
    return render_template("training.html", routines=routines, user=current_user)

@app.route("/leaderboard")
@login_required
def leaderboard():
    all_logs = DailyLog.query.order_by(DailyLog.date.desc()).all()
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_logs = DailyLog.query.filter(DailyLog.date >= one_week_ago).all()
    
    user_scores = {}
    for log in weekly_logs:
        # Score formula: steps / 1000 + protein + intensity * 10
        score = (log.steps / 1000.0) + log.protein + (log.intensity * 10)
        uname = log.author.username
        user_scores[uname] = user_scores.get(uname, 0) + score
        
    winner = None
    if user_scores:
        winner_name = max(user_scores, key=user_scores.get)
        winner = {"name": winner_name, "score": round(user_scores[winner_name], 1)}

    # Leaderboard table ranking
    ranking = sorted([{"name": k, "score": round(v, 1)} for k, v in user_scores.items()], key=lambda x: x["score"], reverse=True)

    return render_template("leaderboard.html", logs=all_logs, winner=winner, ranking=ranking, user=current_user)

@app.route("/history")
@login_required
def history():
    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).all()
    return render_template("history.html", logs=logs, user=current_user)

@app.route("/delete_log/<int:log_id>", methods=["POST"])
@login_required
def delete_log(log_id):
    log_entry = db.session.get(DailyLog, log_id)
    if log_entry and log_entry.user_id == current_user.id:
        db.session.delete(log_entry)
        db.session.commit()
        flash("Log deleted successfully.", "info")
    return redirect(url_for('history'))

@app.route("/cheer/<int:log_id>", methods=["POST"])
@login_required
def cheer(log_id):
    existing = Cheer.query.filter_by(user_id=current_user.id, log_id=log_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    else:
        db.session.add(Cheer(user_id=current_user.id, log_id=log_id))
        db.session.commit()
    return redirect(request.referrer or url_for('leaderboard'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        u = User.query.filter_by(username=username).first()
        if u:
            # Backward compatibility: verify hashed password OR plaintext password
            matched = False
            try:
                matched = check_password_hash(u.password, password)
            except Exception:
                matched = False

            if not matched and u.password == password:
                matched = True
                # Upgrade legacy plain password to modern hash
                u.password = generate_password_hash(password)
                db.session.commit()

            if matched:
                login_user(u)
                flash(f"Welcome back, {u.username}!", "success")
                next_page = request.args.get('next')
                return redirect(next_page or url_for("home"))

        flash("Invalid username or password. Please try again.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 2:
            flash("Username must be at least 2 characters long.", "warning")
            return redirect(url_for("signup"))

        if len(password) < 3:
            flash("Password must be at least 3 characters long.", "warning")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username is already taken. Choose another username.", "danger")
            return redirect(url_for("signup"))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash("Welcome to STRIVE! Let's hit your fitness goals.", "success")
        return redirect(url_for("home"))

    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('food_log', None)
    flash("You have been signed out safely.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
