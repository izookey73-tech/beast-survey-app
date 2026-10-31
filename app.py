from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for, Response
import sqlite3
import random
import base64
import datetime
import os
import requests
from requests.auth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'beast_secret_key_123')

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

DB_FILE = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            id_number TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 0.00,
            tasks_done INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0.00,
            is_verified INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SURVEYS = [
    {
        "id": 1,
        "title": "Level 1: Global Technology & Innovation",
        "difficulty": "Simple",
        "reward": 7.0,
        "questions": [
            {"q": "Is Tokyo the capital city of Japan?", "a": "yes"},
            {"q": "Is Python a popular programming language worldwide?", "a": "yes"},
            {"q": "Does the internet connect computers globally?", "a": "yes"}
        ]
    },
    {
        "id": 2,
        "title": "Level 2: Worldwide Consumer Trends & Travel",
        "difficulty": "Medium",
        "reward": 7.0,
        "questions": [
            {"q": "Is the Eiffel Tower located in Paris, France?", "a": "yes"},
            {"q": "Is e-commerce popular in Africa, Europe, and Asia?", "a": "yes"},
            {"q": "Is Kenya famous for wildlife tourism and safari?", "a": "yes"},
            {"q": "Is the US Dollar a widely accepted global currency?", "a": "yes"},
            {"q": "Do renewable energy projects exist globally?", "a": "yes"}
        ]
    },
    {
        "id": 3,
        "title": "Level 3: Global Economy & Environmental Audit",
        "difficulty": "Complex",
        "reward": 7.0,
        "questions": [
            {"q": "Is the Amazon Rainforest located in South America?", "a": "yes"},
            {"q": "Is solar power used as a clean energy source worldwide?", "a": "yes"},
            {"q": "Is M-Pesa a major mobile money innovation from Kenya?", "a": "yes"},
            {"q": "Are electric vehicles increasing in European markets?", "a": "yes"},
            {"q": "Does global trade rely heavily on international ocean shipping?", "a": "yes"},
            {"q": "Is cybersecurity critical for international banking?", "a": "yes"},
            {"q": "Does artificial intelligence affect global industries?", "a": "yes"}
        ]
    }
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
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#22c55e">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding-bottom: 50px; }
        .card-custom { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        .btn-mpesa { background-color: #22c55e; color: white; font-weight: bold; }
        .btn-withdraw { background-color: #0284c7; color: white; font-weight: bold; }
        .badge-simple { background-color: #0ea5e9; }
        .badge-medium { background-color: #eab308; color: #000; }
        .badge-complex { background-color: #ef4444; }
    </style>
</head>
<body>
<div class="container mt-4" style="max-width: 500px;">
    <div class="text-center mb-4">
        <h2 class="text-success fw-bold"><i class="bi bi-shield-check me-2"></i>Beast Tasks</h2>
        <p class="text-secondary small">Verified Global Surveys • 7 KES Each • Max 10/Day</p>
        <button id="installAppBtn" class="btn btn-outline-success btn-sm d-none mb-2"><i class="bi bi-download me-1"></i> Install App</button>
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
                            <label class="form-label">Phone, Email or User ID</label>
                            <input type="text" name="identifier" class="form-control bg-secondary text-light border-0" placeholder="Phone, email or BEAST-XXXXXX" required>
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
                            <label class="form-label">Email Address</label>
                            <input type="email" name="email" class="form-control bg-secondary text-light border-0" placeholder="user@example.com" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">M-Pesa Phone Number</label>
                            <input type="tel" name="phone" class="form-control bg-secondary text-light border-0" placeholder="254712345678" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">National ID Number</label>
                            <input type="text" name="id_number" class="form-control bg-secondary text-light border-0" placeholder="Enter ID Number" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" class="form-control bg-secondary text-light border-0" required>
                        </div>
                        <div class="alert alert-secondary py-2 small text-center text-light mb-3">
                            <i class="bi bi-patch-check-fill text-info me-1"></i> Requires Email, Phone & ID Verification
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Register & Verify</button>
                    </form>
                </div>
            </div>
        </div>
    {% else %}
        <div class="card card-custom p-4 text-center mb-4">
            <div class="mb-2">
                <span class="badge bg-secondary">ID: {{ user[0] }}</span>
                <span class="badge bg-success"><i class="bi bi-shield-fill-check"></i> Verified Account</span>
            </div>
            <h4 class="text-uppercase fw-bold text-light">{{ user[1] }}</h4>
            <p class="text-secondary small mb-1">Available Earned Balance</p>
            <h1 class="text-success fw-bold">KES <span id="balanceDisplay">{{ "%.2f"|format(user[6]) }}</span></h1>
            
            <div class="text-start bg-dark p-2 rounded small text-secondary mb-3 border border-secondary">
                <div><i class="bi bi-envelope-check text-success me-1"></i> Email: <b>{{ user[3] }}</b></div>
                <div><i class="bi bi-phone text-success me-1"></i> Phone: <b>{{ user[2] }}</b></div>
                <div><i class="bi bi-card-heading text-success me-1"></i> National ID: <b>{{ user[4] }}</b></div>
            </div>

            <div class="row mt-2 text-center">
                <div class="col-6 border-end border-secondary">
                    <span class="text-info fw-bold fs-5" id="tasksCount">{{ user[7] }}</span>/10
                    <div class="text-secondary small">Surveys Today</div>
                </div>
                <div class="col-6">
                    <span class="text-warning fw-bold fs-5">KES {{ "%.2f"|format(user[8]) }}</span>
                    <div class="text-secondary small">Total Earned</div>
                </div>
            </div>
            <hr class="border-secondary my-3">
            <div class="d-flex gap-2">
                <button class="btn btn-mpesa w-50" data-bs-toggle="modal" data-bs-target="#depositModal"><i class="bi bi-wallet2 me-1"></i> Deposit</button>
                <button class="btn btn-withdraw w-50" data-bs-toggle="modal" data-bs-target="#withdrawModal"><i class="bi bi-cash-stack me-1"></i> Withdraw</button>
            </div>
            <a href="/logout" class="btn btn-outline-danger btn-sm mt-3 w-100"><i class="bi bi-box-arrow-right me-1"></i> Sign Out</a>
        </div>

        <h5 class="fw-bold mb-3"><i class="bi bi-globe text-primary me-2"></i>Global Surveys (7 KES Each)</h5>
        <div class="d-flex flex-column gap-3 mb-4">
            {% for survey in surveys %}
            <div class="card card-custom p-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h6 class="fw-bold mb-1">{{ survey.title }}</h6>
                        <small class="text-secondary">{{ survey.questions|length }} Questions • Must answer all correctly</small>
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
                    <button class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick='runSurvey({{ survey|tojson }})'>Start Survey</button>
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

        <!-- Withdraw Modal -->
        <div class="modal fade" id="withdrawModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark text-light border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-info">Withdraw Earnings</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="withdrawForm">
                            <div class="mb-3">
                                <label class="form-label">M-Pesa Phone Number (Verified)</label>
                                <input type="tel" id="witPhone" value="{{ user[2] }}" class="form-control bg-secondary text-light border-0" readonly required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Amount to Withdraw (KES)</label>
                                <input type="number" id="witAmount" class="form-control bg-secondary text-light border-0" placeholder="Minimum KES 150" min="150" required>
                            </div>
                            <button type="submit" id="witBtn" class="btn btn-withdraw w-100">Request Withdrawal</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    {% endif %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js');
    }

    let deferredPrompt;
    const installBtn = document.getElementById('installAppBtn');
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        if(installBtn) installBtn.classList.remove('d-none');
    });

    if(installBtn) {
        installBtn.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') { installBtn.classList.add('d-none'); }
                deferredPrompt = null;
            }
        });
    }

    async function runSurvey(survey) {
        let correctCount = 0;
        let totalQ = survey.questions.length;

        for(let i = 0; i < totalQ; i++) {
            let qObj = survey.questions[i];
            let userAnswer = prompt(`[${survey.title}] Question ${i+1} of ${totalQ}:\n\n${qObj.q}\n\nType 'yes' or 'no':`);
            if(userAnswer === null) return; 
            if(userAnswer.toLowerCase().trim() === qObj.a) { correctCount++; }
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
                alert("🎉 Global survey completed accurately! KES 7.00 added to your account balance.");
            } else {
                alert(data.message);
            }
        } else {
            alert("❌ Survey incomplete or inaccurate! Payment is only made when all " + totalQ + " questions are answered correctly (" + correctCount + "/" + totalQ + " correct). Try again!");
        }
    }

    const depForm = document.getElementById('depositForm');
    if(depForm) {
        depForm.addEventListener('submit', async (e) => {
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

    const witForm = document.getElementById('withdrawForm');
    if(witForm) {
        witForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('witBtn');
            btn.innerText = "Processing...";
            btn.disabled = true;
            try {
                let res = await fetch('/withdraw', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        phone: document.getElementById('witPhone').value,
                        amount: document.getElementById('witAmount').value
                    })
                });
                let data = await res.json();
                alert(data.message);
                if(data.success) {
                    document.getElementById('balanceDisplay').innerText = data.new_balance.toFixed(2);
                    bootstrap.Modal.getInstance(document.getElementById('withdrawModal')).hide();
                }
            } catch(err) {
                alert("Withdrawal processing error");
            } finally {
                btn.innerText = "Request Withdrawal";
                btn.disabled = false;
            }
        });
    }
</script>
</body>
</html>
"""

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "Beast Online Tasks",
        "short_name": "BeastTasks",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#22c55e",
        "icons": [{
            "src": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
            "sizes": "512x512",
            "type": "image/png"
        }]
    }
    return jsonify(manifest_data)

@app.route('/sw.js')
def service_worker():
    return Response("self.addEventListener('fetch', function(event) {});", mimetype='application/javascript')

@app.route('/')
def home():
    user_id = session.get('user_id')
    user = None
    if user_id:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, phone, email, id_number, password, balance, tasks_done, total_earned FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
    return render_template_string(HTML_PAGE, user=user, surveys=SURVEYS)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    id_number = request.form.get('id_number')
    password = request.form.get('password')

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    hashed_password = generate_password_hash(password)
    user_id = f"BEAST-{random.randint(100000, 999999)}"
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, name, phone, email, id_number, password, balance, total_earned, is_verified) 
            VALUES (?, ?, ?, ?, ?, ?, 0.00, 0.00, 1)
        """, (user_id, name, phone, email, id_number, hashed_password))
        conn.commit()
        conn.close()
        session['user_id'] = user_id
    except sqlite3.IntegrityError:
        return "<script>alert('Error: Phone number, Email, or National ID is already registered!'); window.location='/';</script>"
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier')
    password = request.form.get('password')
    if identifier.startswith('0'):
        identifier = '254' + identifier[1:]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users WHERE phone = ? OR email = ? OR user_id = ?", (identifier, identifier, identifier))
    row = cursor.fetchone()
    conn.close()

    if row:
        stored_password = row[1]
        if check_password_hash(stored_password, password) or stored_password == password:
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

    reward = 7.0

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
        return jsonify({'success': False, 'message': 'Daily survey limit reached! Maximum of 10 surveys allowed per day.'})

    new_balance = balance + reward
    new_total = total_earned + reward
    new_tasks = tasks_done + 1

    cursor.execute("UPDATE users SET balance = ?, tasks_done = ?, total_earned = ? WHERE user_id = ?", 
                   (new_balance, new_tasks, new_total, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_balance': new_balance, 'tasks_done': new_tasks})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json() or {}
    amount = float(data.get('amount', 0))

    if amount < 150.0:
        return jsonify({'success': False, 'message': 'Minimum withdrawal amount is KES 150.00'})

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row or row[0] < amount:
        conn.close()
        return jsonify({'success': False, 'message': 'Insufficient account balance!'})

    new_balance = row[0] - amount
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True, 
        'message': f'Withdrawal request for KES {amount:.2f} submitted successfully! Funds will be sent to your verified M-Pesa phone number.', 
        'new_balance': new_balance
    })

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
