import numpy as np
import soundfile as sf
import hashlib
import time

def encode_to_ultrasound(message, filename="out.wav"):
    binary_msg = ''.join(format(ord(i), '08b') for i in message)
    fs = 44100
    t = np.linspace(0, 0.05, int(fs * 0.05))
    audio_signal = np.array([])
    for bit in binary_msg:
        freq = 19500 if bit == '1' else 18500
        audio_signal = np.concatenate((audio_signal, 0.5 * np.sin(2 * np.pi * freq * t)))
    sf.write(filename, audio_signal, fs)
    print(f"--- [AAP] Mensaje convertido a frecuencia invisible: {filename} ---")

def generate_ghost_id():
    cycle = int(time.time() / 60)
    return hashlib.sha256(f"Chrono-Daniel-{cycle}".encode()).hexdigest()[:12]
