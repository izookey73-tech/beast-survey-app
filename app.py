
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import sqlite3
import random
import base64
import datetime
import os
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'beast_secret_key_123')

DB_FILE = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 150.00,
            tasks_done INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 150.00
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Surveys set to 7 KES reward, simple to complex, max 7 questions
SURVEYS = [
    {"id": 1, "title": "Level 1: Basic Brand Recognition", "difficulty": "Simple", "reward": 7.0, "questions": 3},
    {"id": 2, "title": "Level 2: Consumer Shopping Habits", "difficulty": "Medium", "reward": 7.0, "questions": 5},
    {"id": 3, "title": "Level 3: Advanced Software Usability Audit", "difficulty": "Complex", "reward": 7.0, "questions": 7}
]

CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
BUSINESS_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Beast Online Tasks</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding-bottom: 50px; }
        .card-custom { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        .btn-mpesa { background-color: #22c55e; color: white; font-weight: bold; }
        .badge-simple { background-color: #0ea5e9; }
        .badge-medium { background-color: #eab308; color: #000; }
        .badge-complex { background-color: #ef4444; }
    </style>
</head>
<body>
<div class="container mt-4" style="max-width: 500px;">
    <div class="text-center mb-4">
        <h2 class="text-success fw-bold"><i class="bi bi-rocket-takeoff-fill me-2"></i>Beast Tasks</h2>
        <p class="text-secondary small">Surveys • 7 KES Each • Max 10/Day</p>
    </div>

    {% if not session.get('user_id') %}
        <div class="card card-custom p-4">
            <ul class="nav nav-pills nav-justified mb-3" id="authTab" role="tablist">
                <li class="nav-item"><button class="nav-link active text-light" data-bs-toggle="pill" data-bs-target="#login">Sign In</button></li>
                <li class="nav-item"><button class="nav-link text-light" data-bs-toggle="pill" data-bs-target="#register">Register</button></li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="login">
                    <form action="/login" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Phone or User ID</label>
                            <input type="text" name="identifier" class="form-control bg-secondary text-light border-0" placeholder="2547... or BEAST-XXXXXX" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" class="form-control bg-secondary text-light border-0" required>
                        </div>
                        <button type="submit" class="btn btn-success w-100">Sign In</button>
                    </form>
                </div>
                <div class="tab-pane fade" id="register">
                    <form action="/register" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Full Name</label>
                            <input type="text" name="name" class="form-control bg-secondary text-light border-0" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">M-Pesa Phone</label>
                            <input type="tel" name="phone" class="form-control bg-secondary text-light border-0" placeholder="254712345678" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" class="form-control bg-secondary text-light border-0" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Create Account</button>
                    </form>
                </div>
            </div>
        </div>
    {% else %}
        <div class="card card-custom p-4 text-center mb-4">
            <span class="badge bg-secondary mb-1">ID: {{ user[0] }}</span>
            <h4 class="text-uppercase fw-bold text-light">{{ user[1] }}</h4>
            <p class="text-secondary small mb-1">Available Balance</p>
            <h1 class="text-success fw-bold">KES <span id="balanceDisplay">{{ "%.2f"|format(user[4]) }}</span></h1>
            <div class="row mt-3 text-center">
                <div class="col-6 border-end border-secondary">
                    <span class="text-info fw-bold fs-5" id="tasksCount">{{ user[5] }}</span>/10
                    <div class="text-secondary small">Surveys Today</div>
                </div>
                <div class="col-6">
                    <span class="text-warning fw-bold fs-5">KES {{ "%.2f"|format(user[6]) }}</span>
                    <div class="text-secondary small">Total Earned</div>
                </div>
            </div>
            <hr class="border-secondary my-3">
            <div class="d-flex gap-2">
                <button class="btn btn-mpesa w-50" data-bs-toggle="modal" data-bs-target="#depositModal"><i class="bi bi-wallet2 me-1"></i> Deposit</button>
                <a href="/logout" class="btn btn-outline-danger w-50"><i class="bi bi-box-arrow-right me-1"></i> Sign Out</a>
            </div>
        </div>

        <h5 class="fw-bold mb-3"><i class="bi bi-layers-fill text-primary me-2"></i>Available Surveys (7 KES Each)</h5>
        <div class="d-flex flex-column gap-3 mb-4">
            {% for survey in surveys %}
            <div class="card card-custom p-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h6 class="fw-bold mb-1">{{ survey.title }}</h6>
                        <small class="text-secondary">{{ survey.questions }} Questions • Must answer all correctly</small>
                    </div>
                    {% if survey.difficulty == 'Simple' %}
                        <span class="badge badge-simple">Simple</span>
                    {% elif survey.difficulty == 'Medium' %}
                        <span class="badge badge-medium">Medium</span>
                    {% else %}
                        <span class="badge badge-complex">Complex</span>
                    {% endif %}
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <span class="text-success fw-bold">+ KES 7.00</span>
                    <button class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick="runSurvey({{ survey.id }}, '{{ survey.title }}', {{ survey.questions }})">Start Survey</button>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Deposit Modal -->
        <div class="modal fade" id="depositModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark text-light border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-success">M-Pesa Deposit</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="depositForm">
                            <div class="mb-3">
                                <label class="form-label">Phone Number</label>
                                <input type="tel" id="depPhone" value="{{ user[2] }}" class="form-control bg-secondary text-light border-0" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Amount (KES)</label>
                                <input type="number" id="depAmount" class="form-control bg-secondary text-light border-0" value="100" min="10" required>
                            </div>
                            <button type="submit" id="depBtn" class="btn btn-mpesa w-100">Send STK Push</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    {% endif %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    async function runSurvey(id, title, totalQ) {
        let correctCount = 0;
        for(let i = 1; i <= totalQ; i++) {
            let userAnswer = prompt(`[${title}] Question ${i} of ${totalQ}:\nType 'yes' or 'correct' to answer correctly:`);
            if(userAnswer === null) return; 
            if(userAnswer.toLowerCase().trim() === 'yes' || userAnswer.toLowerCase().trim() === 'correct') {
                correctCount++;
            }
        }

        if(correctCount === totalQ) {
            let res = await fetch('/complete-task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            });
            let data = await res.json();
            if(data.success) {
                document.getElementById('balanceDisplay').innerText = data.new_balance.toFixed(2);
                document.getElementById('tasksCount').innerText = data.tasks_done;
                alert("🎉 Survey completed accurately! KES 7.00 has been added to your balance.");
            } else {
                alert(data.message);
            }
        } else {
            alert("❌ Survey failed! Payment is only made for correct survey answers (" + correctCount + "/" + totalQ + " correct). Try again!");
        }
    }

    const form = document.getElementById('depositForm');
    if(form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('depBtn');
            btn.innerText = "Sending STK...";
            btn.disabled = true;
            try {
                let res = await fetch('/stk-push', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        phone: document.getElementById('depPhone').value,
                        amount: document.getElementById('depAmount').value
                    })
                });
                let data = await res.json();
                alert(data.message);
                bootstrap.Modal.getInstance(document.getElementById('depositModal')).hide();
            } catch(err) {
                alert("Payment request failed");
            } finally {
                btn.innerText = "Send STK Push";
                btn.disabled = false;
            }
        });
    }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    user_id = session.get('user_id')
    user = None
    if user_id:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, phone, password, balance, tasks_done, total_earned FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
    return render_template_string(HTML_PAGE, user=user, surveys=SURVEYS)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    phone = request.form.get('phone')
    password = request.form.get('password')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    user_id = f"BEAST-{random.randint(100000, 999999)}"
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, name, phone, password) VALUES (?, ?, ?, ?)", (user_id, name, phone, password))
        conn.commit()
        conn.close()
        session['user_id'] = user_id
    except Exception:
        return "<script>alert('Phone already registered!'); window.location='/';</script>"
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier')
    password = request.form.get('password')
    if identifier.startswith('0'):
        identifier = '254' + identifier[1:]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users WHERE phone = ? OR user_id = ?", (identifier, identifier))
    row = cursor.fetchone()
    conn.close()

    if row and row[1] == password:
        session['user_id'] = row[0]
        return redirect(url_for('home'))
    return "<script>alert('Invalid login credentials!'); window.location='/';</script>"

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/complete-task', methods=['POST'])
def complete_task():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    reward = 7.0  # Fixed reward of 7 KES per survey

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, tasks_done, total_earned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'})

    balance, tasks_done, total_earned = row

    if tasks_done >= 10:
        conn.close()
        return jsonify({'success': False, 'message': 'Daily limit reached! Maximum of 10 surveys allowed per day.'})

    new_balance = balance + reward
    new_total = total_earned + reward
    new_tasks = tasks_done + 1

    cursor.execute("UPDATE users SET balance = ?, tasks_done = ?, total_earned = ? WHERE user_id = ?", 
                   (new_balance, new_tasks, new_total, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_balance': new_balance, 'tasks_done': new_tasks})

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.get_json() or {}
    phone = data.get('phone', '')
    amount = data.get('amount', '100')
    if phone.startswith('0'):
        phone = '254' + phone[1:]

    try:
        r = requests.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), timeout=10)
        token = r.json().get('access_token')
        if not token:
            return jsonify({'message': 'Daraja Auth Failed'}), 400

        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        pwd = base64.b64encode((BUSINESS_SHORTCODE + PASSKEY + timestamp).encode()).decode()
        
        res = requests.post('https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest', json={
            "BusinessShortCode": BUSINESS_SHORTCODE,
            "Password": pwd,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": BUSINESS_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": "https://beast-survey-app.onrender.com/callback",
            "AccountReference": session.get('user_id', 'BEAST'),
            "TransactionDesc": "Deposit"
        }, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, timeout=10)

        res_data = res.json()
        if res_data.get('ResponseCode') == '0':
            return jsonify({'message': 'STK Push sent successfully!'})
        return jsonify({'message': f"Error: {res_data.get('errorMessage', 'Unknown')}"})
    except Exception:
        return jsonify({'message': 'Connection error'}), 500

@app.route('/callback', methods=['POST'])
def callback():
    return jsonify({"ResultCode": 0})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
