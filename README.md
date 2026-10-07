# ⚡ STRIVE — Next-Gen Fitness, Nutrition & Habit Platform

<p align="center">
  <strong>An intuitive, full-stack fitness companion designed for relentless consistency, precise macro logging, structured training, and habit mastery.</strong>
</p>

---

## 🌟 Key Features

### 📊 1. Daily Performance Dashboard
- **Target Macro Progress**: Live dynamic progress indicators tracking calories consumed, protein intake, hydration levels, and daily step volume.
- **Hydration Station**: Interactive water intake tracker with quick increments (`+0.25L`, `+0.50L`, `+0.75L`, `Reset`) and real-time visualization.
- **Daily Check-In & Workout Logger**: Record daily sessions with steps, workout split tags, training intensity slider (1–10), sleep duration, body weight, and personal reflections.
- **Custom Goal Tuning**: Directly customize your daily targets (Calorie goal, Protein goal, Steps, Water) straight from the dashboard.

### 🥗 2. Smart Nutrition & Diet Templates
- **Instant Nutrition Lookup**: Automatic macro search with offline database fallback for common fitness foods (eggs, chicken breast, oats, whey protein, rice, avocado, etc.) + optional CalorieNinjas API integration.
- **Custom Macros Input**: Add custom meal items with precise calorie and protein values.
- **Saved Meal Templates**: Save reusable meals (e.g. "Post-Workout Shake", "Chicken Rice Bowl") for instant 1-click logging.

### 🏋️ 3. Training Lab & Interactive Rest Timer
- **Curated Workout Splits**: Pre-configured routines for **Push Day**, **Pull Day**, **Leg Day**, and **HIIT & Core Conditioning**.
- **Interactive Checklists**: Check off sets and reps dynamically during training sessions.
- **Integrated Rest Timer**: Smart interval countdown timer (`30s`, `60s`, `90s`, `120s`) with audio-visual notifications.
- **Direct Routine Sync**: 1-click transfer from Training Lab directly into today's check-in form.

### 📈 4. Visual Progress Analytics
- **Dynamic Chart.js Visualizations**:
  - **Weight & Intensity Progression**: Multi-axis spline line chart tracking body weight trends against workout effort.
  - **Nutritional Adherence**: Dual-axis bar and line charts comparing calorie consumption with protein intake over time.
  - **Daily Step History**: Volume area chart tracking step count trends.
- **Key Metric Indicators**: Tracks current body weight, overall weight delta, habit consistency streaks, average daily steps, and average protein intake.

### 📜 5. Comprehensive History Timeline
- Chronological timeline of all completed daily logs.
- Macro breakdowns, workout splits, hydration, sleep, and workout reflections.
- Full entry management with deletion capabilities.

### 🏆 6. Community Feed & Weekly Champion Leaderboard
- **Weekly Champion Podium**: Celebrates top performers scored via activity steps, protein intake, and training intensity.
- **Weekly Standings**: Dynamic community leaderboard rankings.
- **Social Feed & Cheers**: Share workout milestones and send cheers (`❤️`) to fellow athletes.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Installation & Setup
```bash
# Clone the repository
git clone https://github.com/aayushdonhai/strive.git
cd strive

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application Locally
```bash
python app.py
```
Open your browser and navigate to **`http://localhost:5000`**.

### 4. Demo Login Credentials
- **Username**: `Aayush`
- **Password**: `123`
*(Or click "Create one here" on the login screen to register a new account!)*

---

## 🛠️ Tech Stack & Architecture
- **Backend**: Python, Flask, Flask-Login, Flask-SQLAlchemy, Werkzeug Security
- **Database**: SQLite (with automatic schema migration)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System, Dark Mode, Glassmorphism, Micro-animations), Chart.js
- **Icons & Typography**: FontAwesome 6, Google Fonts (Outfit & Inter)

---

## 🔒 Security & Best Practices
- Secure password hashing with PBKDF2/SHA256 (`werkzeug.security`).
- Session isolation and authenticated route guarding (`@login_required`).
- Zero hardcoded external secrets; environment variable configuration via `.env`.
- Database files, cache artifacts, and environment files properly git-ignored.

---

## 📄 License
This project is open-source under the MIT License.
