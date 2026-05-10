#!/data/data/com.termux/files/usr/bin/bash

pkill -f python
pkill -f cloudflared

python app.py &
sleep 5

cloudflared tunnel --url http://127.0.0.1:5000
