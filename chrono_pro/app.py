from flask import Flask, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clave_ultra_segura"

def init():
    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user TEXT, pass TEXT)")
    conn.commit()
    conn.close()

init()

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pass"]

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()
        c.execute("SELECT pass FROM users WHERE user=?", (u,))
        r = c.fetchone()
        conn.close()

        if r and check_password_hash(r[0], p):
            session["user"] = u
            return redirect("/panel")

        return "<h3 style='color:red;text-align:center;'>Error login</h3>"

    return BASE_HTML.replace("{{content}}", LOGIN_HTML)

@app.route("/registro", methods=["GET","POST"])
def registro():
    if request.method == "POST":
        u = request.form["user"]
        p = generate_password_hash(request.form["pass"])

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?,?)", (u,p))
        conn.commit()
        conn.close()

        return redirect("/")

    return BASE_HTML.replace("{{content}}", REG_HTML)

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    return BASE_HTML.replace("{{content}}", PANEL_HTML)

BASE_HTML = """
<html>
<head>
<title>Chrono Shield</title>
<style>
body{margin:0;background:#020617;color:white;text-align:center;font-family:Arial;}
.card{background:#000;border:1px solid #00f0ff;margin:20px;padding:20px;border-radius:10px;display:inline-block;}
button{padding:10px;background:#00f0ff;border:none;color:black;}
</style>
</head>
<body>
<h1>CHRONO SHIELD</h1>
{{content}}
</body>
</html>
"""

LOGIN_HTML = """
<h2>Login</h2>
<form method="POST">
<input name="user"><br>
<input name="pass" type="password"><br>
<button>Entrar</button>
</form>
<a href="/registro">Crear cuenta</a>
"""

REG_HTML = """
<h2>Registro</h2>
<form method="POST">
<input name="user"><br>
<input name="pass" type="password"><br>
<button>Registrar</button>
</form>
"""

PANEL_HTML = """
<h2>Panel</h2>

<div class="card">
<h3>Pagos</h3>
<a href="https://www.paypal.com">
<button>Pagar servicio</button>
</a>
</div>
"""

app.run(host="0.0.0.0", port=5000)
