#!/bin/bash
cd ~/Chrono-Shield-Onion
source .env.local
export PYTHONPATH=/data/data/com.termux/files/home/Chrono-Shield-Onion/backend

while true; do
  if ! pgrep -f "python.*api.py" > /dev/null; then
    sleep 3
    echo "$(date): api.py caído, reiniciando..." >> ~/chrono_watchdog.log
    cd backend && nohup python api.py > ~/chrono_api.log 2>&1 &
    cd ..
  fi
  if ! pgrep -f "python.*mesh_server.py" > /dev/null; then
    sleep 3
    echo "$(date): mesh_server.py caído, reiniciando..." >> ~/chrono_watchdog.log
    cd backend && nohup python mesh_server.py > ~/chrono_mesh.log 2>&1 &
    cd ..
  fi
  sleep 10
done
