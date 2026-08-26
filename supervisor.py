import subprocess
import time
import os
import signal

os.chdir(os.path.expanduser("~/Chrono-Shield-Onion/backend"))
env = os.environ.copy()
env["PYTHONPATH"] = os.path.expanduser("~/Chrono-Shield-Onion/backend")

def load_env():
    path = os.path.expanduser("~/Chrono-Shield-Onion/.env.local")
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
                if "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    env[k] = v

load_env()

procs = {}

def spawn(name, cmd):
    log = open(os.path.expanduser(f"~/chrono_{name}.log"), "a")
    p = subprocess.Popen(["python", cmd], env=env, stdout=log, stderr=subprocess.STDOUT)
    procs[name] = p
    print(f"[{time.ctime()}] {name} iniciado (PID {p.pid})")

spawn("api", "api.py")
spawn("mesh", "mesh_server.py")

while True:
    for name, cmd in [("api", "api.py"), ("mesh", "mesh_server.py")]:
        if procs[name].poll() is not None:
            print(f"[{time.ctime()}] {name} murió (código {procs[name].returncode}), reiniciando...")
            time.sleep(2)
            spawn(name, cmd)
    time.sleep(5)
