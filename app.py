

   from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import sqlite3
import random
import base64
import datetime
import os
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'beast_tasks_secret_key_998877')

DB_FILE = 'users.db'

# --- DATABASE SETUP ---
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

# --- DARAJA API CONFIGURATION ---
CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'YOUR_CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'YOUR_CONSUMER_SECRET')
BUSINESS_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')

HTML_APP = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Beast Online Tasks</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding-bottom: 80px; }
        .navbar-custom { background-color: #1e293b; border-bottom: 1px solid #334155; }
        .card-custom { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        .btn-mpesa { background-color: #22c55e; color: white; font-weight: 600; }
        .task-badge { background-color: #0284c7; color: white; border-radius: 20px; padding: 4px 12px; font-size: 0.85rem; }
        .auth-container { max-width: 420px; margin: 50px auto; }
        .user-id-badge { background-color: #334155; color: #38bdf8; font-weight: 600; font-size: 0.8rem; border-radius: 8px; padding: 2px 8px; }
    </style>
</head>
<body>

{% if not session.get('user_id') %}
    <!-- REGISTRATION & LOGIN SCREEN -->
    <div class="container auth-container">
        <div class="text-center mb-4">
            <h2 class="fw-bold text-success"><i class="bi bi-rocket-takeoff-fill me-2"></i>Beast Tasks</h2>
            <p class="text-secondary">Earn KES by completing simple online tasks</p>
        </div>

        <div class="card card-custom p-4">
            <ul class="nav nav-pills nav-justified mb-3" id="authTab">
                <li class="nav-item">
                    <button class="nav-link active text-light" id="login-tab" data-bs-toggle="tab" data-bs-target="#login">Sign In</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link text-light" id="register-tab" data-bs-toggle="tab" data-bs-target="#register">Register</button>
                </li>
            </ul>

            <div class="tab-content">
                <!-- LOGIN FORM -->
                <div class="tab-pane fade show active" id="login">
                    <form action="/login" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Phone Number / User ID</label>
                            <input type="text" name="identifier" class="form-control bg-secondary text-light border-0" placeholder="254712345678 or BEAST-XXXXXX" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" class="form-control bg-secondary text-light border-0" placeholder="••••••••" required>
                        </div>
                        <button type="submit" class="btn btn-success w-100 py-2 font-weight-bold">Sign In</button>
                    </form>
                </div>

                <!-- REGISTER FORM -->
                <div class="tab-pane fade" id="register">
                    <form action="/register" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Full Name</label>
                            <input type="text" name="name" class="form-control bg-secondary text-light border-0" placeholder="Isaac Nyongesa" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">M-Pesa Phone Number</label>
                            <input type="tel" name="phone" class="form-control bg-secondary text-light border-0" placeholder="254712345678" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Create Password</label>
                            <input type="password" name="password" class="form-control bg-secondary text-light border-0" placeholder="••••••••" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100 py-2 font-weight-bold">Create Free Account</button>
                    </form>
                </div>
            </div>
        </div>
    </div>

{% else %}
    <!-- DASHBOARD SCREEN -->
    <nav class="navbar navbar-dark navbar-custom px-3">
        <a class="navbar-brand fw-bold text-success" href="#"><i class="bi bi-rocket-takeoff-fill"></i> Beast Tasks</a>
        <div class="d-flex gap-2 align-items-center">
            <span class="user-id-badge"><i class="bi bi-person-badge me-1"></i>{{ user[0] }}</span>
            <button class="btn btn-sm btn-mpesa rounded-pill px-3" data-bs-toggle="modal" data-bs-target="#mpesaModal"><i class="bi bi-wallet2"></i> Deposit</button>
            <a href="/logout" class="btn btn-sm btn-outline-danger rounded-pill px-2"><i class="bi bi-box-arrow-right"></i></a>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- WELCOME CARD -->
        <div class="card card-custom p-4 mb-4 text-center">
            <span class="text-secondary small">WELCOME BACK, {{ user[1]|upper }}</span>
            <span class="text-secondary d-block small mb-2">User ID: <strong class="text-info">{{ user[0] }}</strong></span>
            <span class="text-secondary small">AVAILABLE BALANCE</span>
            <h1 class="display-5 fw-bold text-success my-1">KES <span id="userBalance">{{ "%.2f"|format(user[4]) }}</span></h1>
            <div class="d-flex justify-content-center gap-3 mt-3">
                <button class="btn btn-outline-light btn-sm rounded-pill px-3" data-bs-toggle="modal" data-bs-target="#mpesaModal"><i class="bi bi-plus-circle"></i> Deposit</button>
                <button class="btn btn-outline-success btn-sm rounded-pill px-3" onclick="alert('Withdrawal request queued!')"><i class="bi bi-arrow-up-right-circle"></i> Cashout</button>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-6">
                <div class="card card-custom p-3 text-center">
                    <i class="bi bi-check2-circle text-info fs-3"></i>
                    <h5 class="fw-bold my-1">{{ user[5] }}</h5>
                    <small class="text-secondary">Tasks Done</small>
                </div>
            </div>
            <div class="col-6">
                <div class="card card-custom p-3 text-center">
                    <i class="bi bi-currency-exchange text-warning fs-3"></i>
                    <h5 class="fw-bold my-1">KES {{ "%.2f"|format(user[6]) }}</h5>
                    <small class="text-secondary">Total Earned</small>
                </div>
            </div>
        </div>

        <h5 class="fw-bold mb-3"><i class="bi bi-list-task text-primary me-2"></i>Available Paid Tasks</h5>
        <div class="d-flex flex-column gap-3">
            <div class="card card-custom p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="fw-bold mb-1">Consumer Shopping Habits Survey</h6>
                        <small class="text-secondary">Est. time: 3 mins • 5 Questions</small>
                    </div>
                    <span class="task-badge">+ KES 50.00</span>
                </div>
                <button class="btn btn-primary btn-sm mt-3 w-100 rounded-pill" onclick="startTask('Consumer Survey', 50)">Start Survey</button>
            </div>
            <div class="card card-custom p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="fw-bold mb-1">Mobile App Usability Review</h6>
                        <small class="text-secondary">Est. time: 5 mins • Rating & Review</small>
                    </div>
                    <span class="task-badge">+ KES 80.00</span>
                </div>
                <button class="btn btn-primary btn-sm mt-3 w-100 rounded-pill" onclick="startTask('App Review', 80)">Start Task</button>
            </div>
        </div>
    </div>

    <!-- M-PESA MODAL -->
    <div class="modal fade" id="mpesaModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content bg-dark text-light border-secondary">
                <div class="modal-header border-secondary">
                    <h5 class="modal-title text-success"><i class="bi bi-phone-vibrate me-2"></i>Lipa Na M-Pesa</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="mpesaForm">
                        <div class="mb-3">
                            <label class="form-label">M-Pesa Phone Number</label>
                            <input type="tel" id="phone" value="{{ user[2] }}" class="form-control bg-secondary text-light border-0" placeholder="254712345678" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Amount (KES)</label>
                            <input type="number" id="amount" class="form-control bg-secondary text-light border-0" placeholder="100" min="10" required>
                        </div>
                        <button type="submit" id="submitBtn" class="btn btn-mpesa w-100 py-2">Trigger STK Push</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
{% endif %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function startTask(taskName, reward) {
            if (confirm("Start task: " + taskName + " for KES " + reward + "?")) {
                let currentBal = parseFloat(document.getElementById('userBalance').innerText);
                document.getElementById('userBalance').innerText = (currentBal + reward).toFixed(2);
                alert("Task completed! KES " + reward + " added to your account balance.");
            }
        }

        const mpesaForm = document.getElementById('mpesaForm');
        if (mpesaForm) {
            mpesaForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                const phone = document.getElementById('phone').value;
                const amount = document.getElementById('amount').value;
                const btn = document.getElementById('submitBtn');

                btn.innerText = "Sending STK Push...";
                btn.disabled = true;

                try {
                    const response = await fetch('/stk-push', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phone: phone, amount: amount })
                    });
                    const data = await response.json();
                    alert(data.message || "STK Push request initiated!");
                    bootstrap.Modal.getInstance(document.getElementById('mpesaModal')).hide();
                } catch (err) {
                    alert("Error reaching payment server.");
                } finally {
                    btn.innerText = "Trigger STK Push";
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
    
    return render_template_string(HTML_APP, user=user)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    phone = request.form.get('phone')
    password = request.form.get('password')

    # Ensure phone starts with 254
    if phone.startswith('0'):
        phone = '254' + phone[1:]

    # Generate Unique User ID
    user_id = f"BEAST-{random.randint(100000, 999999)}"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO users (user_id, name, phone, password) VALUES (?, ?, ?, ?)", 
                       (user_id, name, phone, password))
        conn.commit()
        session['user_id'] = user_id
    except sqlite3.IntegrityError:
        conn.close()
        return "<script>alert('Phone number already registered! Please sign in.'); window.location='/';</script>"

    conn.close()
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
    record = cursor.fetchone()
    conn.close()

    if record and record[1] == password:
        session['user_id'] = record[0]
        return redirect(url_for('home'))
    else:
        return "<script>alert('Invalid phone/User ID or incorrect password!'); window.location='/';</script>"

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.get_json()
    phone = data.get('phone')
    amount = data.get('amount')

    if phone.startswith('0'):
        phone = '254' + phone[1:]

    auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    try:
        r = requests.get(auth_url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
        access_token = r.json().get('access_token')
    except Exception:
        return jsonify({'message': 'Failed to connect to Daraja API'}), 500

    if not access_token:
        return jsonify({'message': 'Invalid Daraja API Credentials'}), 400

    stk_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = BUSINESS_SHORTCODE + PASSKEY + timestamp
    encoded_password = base64.b64encode(password_str.encode()).decode('utf-8')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": encoded_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://beast-survey-app.onrender.com/callback",
        "AccountReference": session.get('user_id', 'BEAST'),
        "TransactionDesc": "Deposit to Beast Tasks"
    }

    res = requests.post(stk_url, json=payload, headers=headers)
    res_data = res.json()

    if res_data.get('ResponseCode') == '0':
        return jsonify({'message': 'STK Push sent successfully! Check your phone for the M-Pesa prompt.'})
    else:
        return jsonify({'message': f"STK Push Error: {res_data.get('errorMessage', 'Unknown error')}"})

@app.route('/callback', methods=['POST'])
def mpesa_callback():
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
 
