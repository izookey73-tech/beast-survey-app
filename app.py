@app.route('/')
def home():
    return "<h1>Beast Online Tasks Platform is Live!</h1><p>API status: Running 24/7</p>"
    
import base64
import datetime
import os
from flask import Flask, jsonify, render_template_string, request
from flask_sqlalchemy import SQLAlchemy
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# ==========================================
# CONFIGURATION & DATABASE SETUP
# ==========================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Safaricom Daraja Credentials
CONSUMER_KEY = os.getenv("CONSUMER_KEY", "YOUR_PRODUCTION_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET", "YOUR_PRODUCTION_CONSUMER_SECRET")
BUSINESS_SHORTCODE = os.getenv("BUSINESS_SHORTCODE", "174379")
PASSKEY = os.getenv("PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")

# ==========================================
# DATABASE MODELS
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    paid_registration = db.Column(db.Boolean, default=True)
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class CompletedTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.String(50), nullable=False)
    earned = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'TASK_REWARD', 'WITHDRAWAL'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

TASKS = [
    {"id": "task_1", "title": "Complete Market Research Survey", "reward": 50.0},
    {"id": "task_2", "title": "Watch Promo Video & Review", "reward": 30.0},
    {"id": "task_3", "title": "App Feedback & Rating Survey", "reward": 45.0}
]

# ==========================================
# API ENDPOINTS
# ==========================================
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json or {}
    phone = data.get("phone")
    name = data.get("name", "User")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone, name=name, paid_registration=True)
        db.session.add(user)
        db.session.commit()

    return jsonify({"message": "Account active!", "phone": user.phone, "name": user.name})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify({"tasks": TASKS})

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    data = request.json or {}
    phone = data.get("phone")
    task_id = data.get("task_id")

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"error": "User account not found."}), 404

    existing_task = CompletedTask.query.filter_by(user_id=user.id, task_id=task_id).first()
    if existing_task:
        return jsonify({"error": "Task already completed."}), 400

    task = next((t for t in TASKS if t["id"] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found."}), 404

    user.balance += task["reward"]
    completed = CompletedTask(user_id=user.id, task_id=task_id, earned=task["reward"])
    txn = Transaction(user_id=user.id, amount=task["reward"], type='TASK_REWARD')

    db.session.add(completed)
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Task completed! Earned KSh {task['reward']}",
        "new_balance": user.balance
    })

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json or {}
    phone = data.get("phone")

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"error": "User account not found."}), 404

    if user.balance <= 0:
        return jsonify({"error": "Insufficient balance to withdraw."}), 400

    amount = user.balance
    user.balance = 0.0

    txn = Transaction(user_id=user.id, amount=amount, type='WITHDRAWAL')
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Withdrawal request of KSh {amount} sent to M-Pesa ({phone})!",
        "remaining_balance": user.balance
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
