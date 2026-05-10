import hashlib, time
import os, random, string
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)
logs = []

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>CHRONO SHIELD | ONION V7</title>
    <style>
        :root { --main: #00ff41; --bg: #000; --low: #080808; }
        body { background: var(--bg); color: var(--main); font-family: 'Courier New', monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        #header { padding: 10px; background: var(--low); border-bottom: 1px solid var(--main); font-size: 10px; display: flex; justify-content: space-between; }
        
        /* Diagnóstico Visual */
        #diag-panel { display: flex; background: #050505; border-bottom: 1px solid #111; padding: 5px; font-size: 9px; gap: 10px; overflow-x: auto; }
        .stat { border: 1px solid #222; padding: 3px 8px; white-space: nowrap; }
        .active { color: #fff; text-shadow: 0 0 5px var(--main); }

        #radar-container { height: 120px; background: radial-gradient(circle, #001a00 0%, #000 80%); position: relative; border-bottom: 1px solid var(--main); display: flex; align-items: center; justify-content: center; }
        .scanner-line { position: absolute; width: 100%; height: 2px; background: var(--main); opacity: 0.3; box-shadow: 0 0 15px var(--main); animation: scan 3s infinite linear; }
        @keyframes scan { 0% { top: 0; } 100% { top: 100%; } }

        #log { flex: 1; padding: 10px; overflow-y: auto; font-size: 11px; scroll-behavior: smooth; }
        .m { margin-bottom: 15px; border-left: 2px solid var(--main); padding-left: 10px; }
        .onion-layer { font-size: 8px; color: #444; }

        footer { padding: 10px; background: var(--low); border-top: 1px solid var(--main); display: flex; gap: 8px; }
        input { flex: 1; background: #000; border: 1px solid var(--main); color: var(--main); padding: 12px; font-size: 14px; outline: none; }
        button { background: var(--main); border: none; padding: 10px 15px; font-weight: bold; color: #000; cursor: pointer; }

        #lock-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    </style>
</head>
<body onclick="initSystem()">

    <div id="lock-screen">
        <h2 style="letter-spacing: 5px;">SISTEMA CHRONO</h2>
        <div style="border: 1px solid var(--main); padding: 25px; text-align: center;">
            <input type="password" id="pass" placeholder="CÓDIGO DE MALLA" style="text-align: center; width: 180px;"><br><br>
            <button onclick="unlock()">ACCEDER AL NODO</button>
        </div>
    </div>

    <div id="header">
        <span>CHRONO ONION v7.0</span>
        <span id="ghost-id">ID: [PENDIENTE]</span>
    </div>

    <div id="diag-panel">
        <div class="stat">MICRO: <span id="st-mic" class="active">OFF</span></div>
        <div class="stat">SONIC: <span class="active">READY</span></div>
        <div class="stat">TUNNEL: <span id="st-tun" class="active">BOG-01</span></div>
        <div class="stat">RELAYS: <span class="active">ONION-L3</span></div>
    </div>

    <div id="radar-container">
        <div class="scanner-line"></div>
        <canvas id="osc" style="width:100%; height:80px;"></canvas>
    </div>

    <div id="log">
        <p style="color:#333; font-size:9px;">[SISTEMA] Esperando inicialización de hardware...</p>
    </div>

    <footer>
        <input type="text" id="i" placeholder="ENVIAR POR CANAL SEGURO..." autocomplete="off">
        <button onclick="transmit()">SEND</button>
    </footer>

    <script>
        let myId = "";
        let audioCtx, analyzer;

        function unlock() {
            if(document.getElementById('pass').value === "CHRONO-2026") {
                document.getElementById('lock-screen').style.display = 'none';
                myId = "NODE-" + Math.random().toString(36).substr(2,4).toUpperCase();
                document.getElementById('ghost-id').innerText = "ID: " + myId;
            }
        }

        async function initSystem() {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                analyzer = audioCtx.createAnalyser();
                
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    const source = audioCtx.createMediaStreamSource(stream);
                    source.connect(analyzer);
                    document.getElementById('st-mic').innerText = "ON";
                    draw();
                } catch(e) { console.log("Mic blocked"); }
            }
        }

        function transmit() {
            const val = document.getElementById('i').value.toUpperCase();
            if(!val) return;
            
            // Frecuencia ultrasónica variable
            let now = audioCtx.currentTime;
            val.split('').forEach(c => {
                const osc = audioCtx.createOscillator();
                osc.frequency.setValueAtTime(18000 + (c.charCodeAt(0) * 12), now);
                const g = audioCtx.createGain();
                g.gain.setValueAtTime(0.08, now);
                g.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
                osc.connect(g).connect(audioCtx.destination);
                osc.start(now); osc.stop(now + 0.12);
                now += 0.15;
            });

            fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: val, user: myId})
            }).then(() => { document.getElementById('i').value = ''; update(); });
        }

        async function update() {
            const r = await fetch('/messages');
            const data = await r.json();
            const log = document.getElementById('log');
            log.innerHTML = data.reverse().map(m => `
                <div class="m">
                    <div class="onion-layer">CAPA DE CEBOLLA: AES-LITE // FROM: ${m.user}</div>
                    <div style="margin:4px 0;">>> ${m.text}</div>
                    <div style="font-size:8px; color:#222;">DATA_CHUNK: ${btoa(m.text).substr(0,16)}...</div>
                </div>
            `).join('');
        }

        function draw() {
            const canvas = document.getElementById('osc');
            const ctx = canvas.getContext('2d');
            const data = new Uint8Array(analyzer.frequencyBinCount);
            requestAnimationFrame(draw);
            analyzer.getByteTimeDomainData(data);
            ctx.clearRect(0,0,canvas.width,canvas.height);
            ctx.strokeStyle = '#00ff41';
            ctx.beginPath();
            let x = 0;
            for(let i=0; i<data.length; i++) {
                let y = (data[i]/128.0) * canvas.height/2;
                if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
                x += canvas.width/data.length;
            }
            ctx.stroke();
        }
        setInterval(update, 3000);
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/messages')
def get_messages(): return jsonify(logs)

@app.route('/send', methods=['POST'])
def send_message():
    d = request.json
    logs.append({"text": d['text'], "user": d['user'], "time": datetime.now().strftime("%H:%M:%S")})
    if len(logs) > 30: logs.pop(0)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)












print(f'--- [GHOST ID ACTIVO]: Chrono-Daniel-' + hashlib.sha256(str(int(time.time() / 60)).encode()).hexdigest()[:8])
