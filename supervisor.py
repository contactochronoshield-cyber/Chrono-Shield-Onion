import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
os.chdir(BACKEND)
env = os.environ.copy()
env["PYTHONPATH"] = BACKEND


def load_env():
    path = os.path.join(ROOT, ".env.local")
    if not os.path.exists(path):
        return  # en Docker las variables vienen del entorno
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"').strip("'")


load_env()
procs = {}


def spawn(name, script):
    if env.get("CHRONO_LOG_TO_STDOUT") == "1":
        out = None
    else:
        out = open(os.path.expanduser(f"~/chrono_{name}.log"), "a")
    p = subprocess.Popen([sys.executable, script], env=env, stdout=out,
                         stderr=subprocess.STDOUT if out else None)
    procs[name] = p
    print(f"[{time.ctime()}] {name} iniciado (PID {p.pid})", flush=True)


SERVICES = [("api", "api.py"), ("mesh", "mesh_server.py")]
for n, s in SERVICES:
    spawn(n, s)

while True:
    for n, s in SERVICES:
        if procs[n].poll() is not None:
            print(f"[{time.ctime()}] {n} murió (código {procs[n].returncode}), reiniciando...", flush=True)
            time.sleep(2)
            spawn(n, s)
    time.sleep(5)
