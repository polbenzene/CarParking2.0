from flask import Flask, render_template, session, request, g 
from flask import redirect, url_for, send_file, make_response
import os
import sqlite3
import qrcode
import base64
import smtplib
import random
import requests
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, auth

app = Flask(__name__)
app.secret_key = os.urandom(24)



# Initialize Firebase


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    session.pop('user', None)
    session.pop('remember_me', None)
    session['remember_me'] = False
    return redirect(url_for('login'))


@app.route('/')
def index():
    if session.get('remember_me'):
        session.permanent = True
        return redirect(url_for('userview'))
    else:
        response = make_response(render_template('loading.html'))
        response.headers['Refresh'] = '8; url=login'
        return response
    
@app.route('/userview')
def userview():
    user_id = session.get('user_id')
    
    response = requests.get('http://127.0.0.1:5000/count')
    count = response.text

    if user_id:
        user = session.get('user')
        return render_template('index.html', user=user, logout=True, count=count)
    return redirect(url_for('index'))


@app.before_request
def before_request():
    g.user = None

    if 'user' in session:
        g.user = session['user']


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        
        # Query Firestore to check if the user exists
        users_ref = db.collection('user_data')  # Use the correct collection name
        query = users_ref.where('email', '==', email).where('password', '==', password).limit(1)
        query_result = query.stream()

        user = None
        for doc in query_result:
            user = doc.to_dict()
            break

        if user:
            session['user_id'] = doc.id
            session['user'] = user['username']
            session['remember_me'] = remember_me
            return redirect(url_for('userview'))
        else:
            error = 'Invalid email or password'
            return render_template('login.html', error=error, is_invalid=True)

    else:
        return render_template('login.html', is_invalid=False)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['name']
        platenumber = request.form['platenumber']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        conpassword = request.form['conpassword']

        if password != conpassword:
            return render_template('signup.html', error='Passwords do not match')

        # Query Firestore to check if email already exists
        users_ref = db.collection('user_data')  # Use the correct collection name
        email_query = users_ref.where('email', '==', email).limit(1)

        existing_email = email_query.stream()

        if any(existing_email):
            return render_template('signup.html', error='Email already exists')

        # Add the user data to Firestore
        user_data = {
            'username': username,
            'platenumber': platenumber,
            'email': email,
            'phone': phone,
            'password': password
        }
        
        users_ref.add(user_data)

        session['user'] = username
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/forgotpass')
def forgotpass():
    return render_template('forgotpass.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    # Get the OTP from the session variable
    stored_otp = session.get('otp')

    # Get the user inputted OTP from the form
    user_otp = request.form['number1'] + request.form['number2'] + request.form['number3'] + request.form['number4'] + request.form['number5'] + request.form['number6']

    # Verify the OTP
    if user_otp == stored_otp:
        # OTP is valid, redirect to login page
        return render_template('resetpassword.html')
    else:
        # OTP is invalid, show an error message
        prompt_message = 'Invalid OTP, please try again.'
        return render_template('otpverify.html', prompt_message=prompt_message)

@app.route('/qrcode')
def generate_qrcode():
    user_id = session.get('user_id')
    
    if user_id:
        # Query Firestore to retrieve user data
        users_ref = db.collection('user_data')  # Use the correct collection name
        query = users_ref.document(user_id).get()
        user_data = query.to_dict()

        data = f"{user_data['username']}, {user_data['platenumber']}, {user_data['email']}, {user_data['phone']}"
        img = qrcode.make(data)

        # Convert the image to a base64 encoded string
        buffer = BytesIO()
        img.save(buffer, 'PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        return render_template('qrcode.html', img_b64=img_b64)
    else:
        return redirect(url_for('login'))
    
@app.route('/download_qrcode', methods=['POST'])
def download_qrcode():
    downloads_dir = Path.home() / "Downloads"
    qrcode_path = downloads_dir / "qrcode.png"

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Query Firestore to get the user's data
    user_ref = db.collection('user_data').document(user_id)
    user_data = user_ref.get().to_dict()
    
    # Generate the QR code and save it to the downloads folder
    data = f"{user_data['username']},{user_data['platenumber']},{user_data['email']},{user_data['phone']}"
    img = qrcode.make(data)
    img.save(qrcode_path)
    
    # Return a response to download the QR code image fil
    return send_file(qrcode_path, as_attachment=True)
    
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        platenumber = request.form['platenumber']

        # Update user data in Firestore
        user_ref = db.collection('user_data').document(user_id)
        user_ref.update({
            'email': email,
            'phone': phone,
            'platenumber': platenumber
        })

        return redirect(url_for('profile'))

    # Retrieve user data from Firestore
    user_ref = db.collection('user_data').document(user_id)
    user_data = user_ref.get().to_dict()

    return render_template('profile.html', user=user_data)

@app.route('/count')
def get_count():
    # get the current count value from the external Flask app
    response = requests.get('http://127.0.0.1:5000/count')
    count = response.text

    # return the count value as a response
    return count

if __name__ == '__main__':
    app.run(port=5001)
