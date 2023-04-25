from flask import Flask, render_template, session, request, g 
from flask import redirect, url_for, send_file, flash, make_response
import os
import sqlite3
import qrcode
import base64
import smtplib
import random
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path



app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE = 'database.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, platenumber TEXT NOT NULL)')
        db.commit()
    return db

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
    if user_id:
        user = session.get('user')
        return render_template('index.html', user=user, logout=True)
    return redirect(url_for('index'))



@app.before_request
def before_request():
    g.user = None

    if 'user' in session:
        g.user = session['user']


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        
        db = get_db()
        cur = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cur.fetchone()

        if user:
            session['user_id'] = user['id']
            session['user'] = user['username']
            session['remember_me'] = remember_me
            return redirect(url_for('userview'))
        else:
            return render_template('login.html', error='Invalid username or password')
    else:
        return render_template('login.html')


@app.route('/forgotpass')
def forgotpass():
    return render_template('forgotpass.html')


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

        db = get_db()

        try:
            db.execute('INSERT INTO users (username, platenumber, email, phone, password) VALUES (?, ?, ?, ?, ?)', (username, platenumber, email, phone, password))
            db.commit()
            session['user'] = username
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            return render_template('signup.html', error='Username already exists')

    return render_template('signup.html')

@app.route('/reset_password', methods=['GET','POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['newPassword']

        db = get_db()
        cur = db.execute('SELECT * FROM users WHERE email = ?', [email])
        user = cur.fetchone()
        if not user:
            flash('Email address not found!')
            return redirect(url_for('reset_password'))
        
        db.execute('UPDATE users SET password = ? WHERE email = ?',(password, email))
        db.commit()

        return render_template('resetpass2.html')
    return render_template('resetpassword.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not g.user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        platenumber = request.form['platenumber']
        db = get_db()
        db.execute('UPDATE users SET email = ?, phone = ?, platenumber = ? WHERE username = ?', (email, phone, platenumber, g.user))
        db.commit()
        return redirect(url_for('profile'))

    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE username = ?', [g.user])
    user = cur.fetchone()

    return render_template('profile.html', user=user)

@app.route('/qrcode',methods=['POST'])
def generate_qrcode():
    # Generate the data and the QR code image
    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE username = ?', [g.user])
    user = cur.fetchone()
    data = f"{user['username']}, {user['platenumber']}, {user['email']}, {user['phone']}"
    img = qrcode.make(data)

    # Convert the image to a base64 encoded string
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    # Pass the base64 encoded string to the HTML template
    return render_template('qrcode.html', img_b64=img_b64)


@app.route('/download_qrcode', methods=['POST'])
def download_qrcode():
    downloads_dir = Path.home() / "Downloads"
    qrcode_path = downloads_dir / "qrcode.png"

    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE username = ?', [g.user])
    user = cur.fetchone()
    
    # Generate the QR code and save it to the downloads folder
    data = f"{user['username']},{user['platenumber']},{user['email']},{user['phone']}"
    img = qrcode.make(data)
    with open(qrcode_path, 'wb') as f:
        img.save(f)
    
    # Return a response to download the QR code image file
    return send_file(qrcode_path, as_attachment=True)


EmailAdd = 'carparkingteam1@gmail.com'
Pass = 'fqwmjbmhpcdxiohd'
Server = 'smtp.gmail.com'

@app.route('/send_otp', methods=['POST'])
def send_otp():
    # Generate a random OTP code
    otp_code = str(random.randint(100000, 999999))

    # Create a new EmailMessage object
    msg = EmailMessage()

    # Set the sender, recipient, and subject of the email
    msg['From'] = EmailAdd
    msg['To'] = request.form['email']
    msg['Subject'] = 'Your OTP Code'

    # Set the content of the email to the OTP code
    msg.set_content(f'Your OTP code is: {otp_code}')

    # Send the email using SMTP
    with smtplib.SMTP(Server, 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(EmailAdd, Pass)
        smtp.send_message(msg)

    #stores the otp code for verification later
    session['otp'] = otp_code
    return render_template('otpverify.html')


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
        error = 'Invalid OTP, please try again.'
        return render_template('otpverify.html', error=error)
    

if __name__ == '__main__':
    app.run(port=5001)
