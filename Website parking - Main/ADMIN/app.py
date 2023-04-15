from flask import Flask, render_template, Response, session, request, g, redirect, url_for
import cv2
import pickle
import os

# counters for parking_availability
counter = 0
occupied = 0

app = Flask(__name__)
app.secret_key = os.urandom(24)

# video source
cap = cv2.VideoCapture('carpark.mp4')

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session.pop('user', None)

        if request.form['password'] == 'password':
            session['user'] = request.form['username']
            return redirect(url_for('adminview'))

    return render_template('LoginPage.html')

@app.route('/adminview')
def adminview():
    if g.user:
        return render_template('index.html', user=session['user'])
    return redirect(url_for('adminview'))

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/omg')
def omg():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

#available space count
@app.route('/count')
def count():
    p = counter
    return str(p)

@app.route('/login')
def login():
    return render_template('login.html')

#occupied space count
@app.route('/occupied')
def occcupied():
    o = occupied
    return str(o)

if __name__ == '__main__':
    app.run(port=5000)