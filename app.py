from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import hashlib, time, os
import numpy as np
import soundfile as sf

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chrono_shield.db'
app.config['SECRET_KEY'] = 'DANIEL_CEO_777'
db = SQLAlchemy(app)

# Modelo de Base de Datos Blindada
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50))
    content = db.Column(db.Text)
    timestamp = db.Column(db.String(20))

with app.app_context():
    db.create_all()

# Motor AAP (Acoustic Anomaly Protocol)
def generate_ultrasound(text):
    filename = f"static/audio/msg_{int(time.time())}.wav"
    os.makedirs('static/audio', exist_ok=True)
    binary_msg = ''.join(format(ord(i), '08b') for i in text)
    fs = 44100
    t = np.linspace(0, 0.05, int(fs * 0.05))
    audio_signal = np.array([])
    for bit in binary_msg:
        freq = 19500 if bit == '1' else 18500
        audio_signal = np.concatenate((audio_signal, 0.5 * np.sin(2 * np.pi * freq * t)))
    sf.write(filename, audio_signal, fs)
    return filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    user = request.form.get('username')
    return redirect(url_for('dashboard', user=user))

@app.route('/dashboard/<user>')
def dashboard(user):
    msgs = Message.query.order_by(Message.id.desc()).limit(10).all()
    uid = hashlib.sha256(user.encode()).hexdigest()[:10]
    avatar = f"https://www.gravatar.com/avatar/{hashlib.md5(user.encode()).hexdigest()}?d=identicon"
    return render_template('dashboard.html', user=user, uid=uid, avatar=avatar, msgs=msgs)

@app.route('/send', methods=['POST'])
def send():
    user = request.form.get('user')
    msg_text = request.form.get('message')
    new_msg = Message(sender=user, content=msg_text, timestamp=time.strftime('%H:%M:%S'))
    db.session.add(new_msg)
    db.session.commit()
    # Generar audio AAP automáticamente
    generate_ultrasound(msg_text)
    return redirect(url_for('dashboard', user=user))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
