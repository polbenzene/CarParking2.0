from flask import Flask, render_template, Response, session, request, g, redirect, url_for
from firebase_admin import credentials, firestore
from google.cloud import firestore
import cv2
import pickle
import os
import firebase_admin


cred = credentials.Certificate('C:/Users/USER/Desktop/CarParking2.0(Updated DataBase)/Website parking - Main/ADMIN/qrscanner-3db7e-firebase-adminsdk-p6guk-6a6f4a9082.json')
firebase_admin.initialize_app(cred)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/USER/Desktop/CarParking2.0(Updated DataBase)/Website parking - Main/ADMIN/qrscanner-3db7e-firebase-adminsdk-p6guk-6a6f4a9082.json"

db = firestore.Client()

# counters for parking_availability
counter = 0
occupied = 0

app = Flask(__name__)
app.secret_key = os.urandom(24)

# video source
cap = cv2.VideoCapture('carpark.mp4')
#cap=cv2.VideoCapture('rtsp://FinalTeam1:Carpark01@192.168.1.68:554/stream1')

# parking space positions
with open('park_positions', 'rb') as f:
    park_positions = pickle.load(f)

# parking space parameters
width, height = 45, 90
full = width * height
empty = 0.22

font = cv2.FONT_HERSHEY_COMPLEX_SMALL

def parking_space_counter(img_processed, overlay):
    global counter, occupied

    counter = 0
    occupied = 0

    for position in park_positions:
        x, y = position

        img_crop = img_processed[y:y + height, x:x + width]
        count = cv2.countNonZero(img_crop)

        ratio = count / full

        if ratio < empty:
            color = (0, 255, 0)
            counter += 1
        else:
            color = (0, 0, 255)

        cv2.rectangle(overlay, position, (position[0] + width, position[1] + height), color, -1)
        #cv2.putText(overlay, "{:.2f}".format(ratio), (x + 4, y + height - 4), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    occupied = len(park_positions) - counter

def generate_frames():
    while True:
        success, frame = cap.read()

        # video looping
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        overlay = frame.copy()

        # frame processing
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        img_blur = cv2.GaussianBlur(img_gray, (3, 3), 1)
        img_thresh = cv2.adaptiveThreshold(img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)

        parking_space_counter(img_thresh, overlay)
        alpha = 0.7
        frame_new = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        ret, buffer = cv2.imencode('.jpg', frame_new)
        frame_new = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_new + b'\r\n')

@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    return render_template('loading.html'),{"Refresh": "8; url=login"}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # clear the user session if password is incorrect or if logout button is clicked
        if request.form['password'] != 'password' or 'logout' in request.form:
            session.pop('user', None)
            session['authenticated'] = False
            g.user = None

        # log the user in if password is correct
        elif request.form['password'] == 'password' and request.form['username'] == 'admin123':
            session['user'] = request.form['username']
            session['authenticated'] = True
            g.user = session['user']
            return redirect(url_for('adminview'))

    # redirect to admin view if user is logged in
    if g.user:
        return redirect(url_for('adminview'))

    # render the login page
    session['authenticated'] = False
    return render_template('login.html')


@app.route('/adminview')
def adminview():
    # check if user is logged in
    if not g.user:
        return redirect(url_for('login'))

    # check if user has been authenticated
    if not session.get('authenticated', False):
        return redirect(url_for('login'))

    return render_template('index.html')


@app.route('/users')
def users():
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('index'))

    # Fetch user data from Firestore
    db = firestore.Client()
    users_ref = db.collection('users')
    users = [user.to_dict() for user in users_ref.stream()]

    return render_template('users.html', users=users)



@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/count')
def count():
    p = counter
    return str(p)


@app.route('/occupied')
def occupied():
    o = occupied
    return str(o)


@app.route('/display_user_data')
def display_user_data():
    users_ref = db.collection('user_data')  # Use the correct collection name
    query_result = users_ref.stream()
    
    data = []
    for doc in query_result:
        user_data = doc.to_dict()
        data.append(user_data)

    return render_template('registeredusers.html', data=data)


if __name__ == '__main__':
    app.run(port=5000)