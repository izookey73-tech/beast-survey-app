from flask import Flask, jsonify, render_template, request
import base64
import datetime
import os
from flask_sqlalchemy import SQLAlchemy
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# CONFIGURATION & DATABASE SETUP
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
