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
    try:
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
    except Exception as e:
        print(f"Database error: {e}")

init_db()

# --- DARAJA API CONFIGURATION ---
CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
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
            <span class="user-id-badge"><i class="bi bi-person-badge me-1"></i>{{ user[0] if user else 'BEAST' }}</span>
            <button class="btn btn-sm btn-mpesa rounded-pill px-3" data-bs-toggle="modal" data-bs-target="#mpesaModal"><i class="bi bi-wallet2"></i> Deposit</button>
            <a href="/logout" class="btn btn-sm btn-outline-danger rounded-pill px-2"><i class="bi bi-box-arrow-right"></i></a>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- WELCOME CARD -->
        <div class="card card-custom p-4 mb-4 text-center">
            <span class="text-secondary small">WELCOME BACK, {{ user[1]|upper if user else 'USER' }}</span>
            <span class="text-secondary d-block small mb-2">User ID: <strong class="text-info">{{ user[0] if user else 'N/A' }}</strong></span>
            <span class="text-secondary small">AVAILABLE BALANCE</span>
            <h1 class="display-5 fw-bold text-success my-1">KES <span id="userBalance">{{ "%.2f"|format(user[4]) if user else '150.00' }}</span></h1>
            <div class="d-flex justify-content-center gap-3 mt-3">
                <button class="btn btn-outline-light

 
