#!/bin/bash

export PORT=${PORT:-8080}

# اجرای Xray در پس‌زمینه
xray -c /usr/local/etc/xray/config.json &

# اجرای پنل FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
