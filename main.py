import json
import os
import subprocess
import uuid as uuid_lib
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional

app = FastAPI(title="Spider Panel Pro")

# ========== تنظیمات ==========
CONFIG_PATH = "/usr/local/etc/xray/config.json"
DATA_FILE = "/app/data.json"
PASSWORD_FILE = "/app/password.txt"
templates = Jinja2Templates(directory="templates")  # برای قالب‌های HTML

# ========== مدیریت داده‌ها ==========

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"inbounds": [], "users": {}, "settings": {"password": "admin", "lang": "fa"}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_password():
    data = load_data()
    return data.get("settings", {}).get("password", "admin")

def set_password(new_pass):
    data = load_data()
    if "settings" not in data:
        data["settings"] = {}
    data["settings"]["password"] = new_pass
    save_data(data)

def get_domain():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL") or "localhost"
    return domain.replace("https://", "").replace("http://", "")

# ========== مدیریت Xray ==========

def generate_xray_config():
    data = load_data()
    inbounds = []
    
    for inbound in data.get("inbounds", []):
        inbound_config = {
            "listen": "127.0.0.1",
            "port": inbound.get("port", 10086),
            "protocol": inbound.get("protocol", "vless"),
            "settings": {
                "clients": [],
                "decryption": "none" if inbound.get("protocol") != "shadowsocks" else None
            },
            "streamSettings": {
                "network": inbound.get("network", "ws"),
                "wsSettings": {"path": inbound.get("path", "/ws")} if inbound.get("network") == "ws" else {},
                "tlsSettings": {} if not inbound.get("tls") else {
                    "serverName": inbound.get("sni", get_domain())
                }
            }
        }
        
        for user_id in inbound.get("users", []):
            user_data = data["users"].get(user_id, {})
            client = {
                "id": user_id,
                "email": user_data.get("email", f"user_{user_id[:8]}")
            }
            if inbound.get("protocol") == "vless":
                client["flow"] = user_data.get("flow", "xtls-rprx-vision")
            inbound_config["settings"]["clients"].append(client)
        
        inbounds.append(inbound_config)
    
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": inbounds,
        "outbounds": [{"protocol": "freedom"}]
    }
    
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    restart_xray()

def restart_xray():
    subprocess.run(["pkill", "-f", "xray"], capture_output=True)
    subprocess.Popen(["xray", "-c", CONFIG_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ========== توابع کمکی ==========

def check_auth(password: str = ""):
    return password == get_password()

def get_lang_from_cookie(lang: Optional[str] = None):
    return lang if lang in ['fa', 'en'] else 'fa'

# ========== قالب HTML (داخلی) ==========

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕸️ Spider Panel Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            direction: {{ 'rtl' if lang == 'fa' else 'ltr' }};
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #1e293b;
            padding: 15px 25px;
            border-radius: 16px;
            border: 1px solid #334155;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header h1 { font-size: 24px; display: flex; align-items: center; gap: 10px; }
        .header h1 small { font-size: 14px; color: #94a3b8; font-weight: normal; }
        .header-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .header-actions a, .header-actions button {
            background: #334155;
            border: none;
            color: #94a3b8;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 13px;
            cursor: pointer;
            text-decoration: none;
            transition: 0.2s;
        }
        .header-actions a:hover, .header-actions button:hover {
            background: #475569;
            color: #e2e8f0;
        }
        .header-actions .danger:hover { background: #dc2626; color: white; }
        .lang-btn {
            background: #334155;
            border: none;
            color: #94a3b8;
            padding: 4px 12px;
            border-radius: 30px;
            font-size: 12px;
            cursor: pointer;
            text-decoration: none;
        }
        .lang-btn.active { background: #3b82f6; color: white; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #1e293b;
            padding: 15px;
            border-radius: 16px;
            border: 1px solid #334155;
            text-align: center;
        }
        .stat-card .number { font-size: 28px; font-weight: bold; color: #3b82f6; }
        .stat-card .label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
        .card {
            background: #1e293b;
            border-radius: 16px;
            border: 1px solid #334155;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            border-bottom: 1px solid #334155;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #1e293b;
        }
        th { color: #94a3b8; font-weight: 600; font-size: 13px; }
        tr:hover { background: #0f172a; }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 30px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-vless { background: #3b82f6; color: white; }
        .badge-vmess { background: #8b5cf6; color: white; }
        .badge-trojan { background: #ef4444; color: white; }
        .badge-ss { background: #22c55e; color: #052e16; }
        .btn {
            background: #3b82f6;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #2563eb; }
        .btn-sm { padding: 4px 12px; font-size: 12px; }
        .btn-danger { background: #ef4444; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #475569; }
        .btn-secondary:hover { background: #334155; }
        .btn-success { background: #22c55e; }
        .btn-success:hover { background: #16a34a; }
        form { display: inline; }
        input, select {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 8px 14px;
            color: #e2e8f0;
            font-size: 14px;
            width: 100%;
        }
        input:focus, select:focus { outline: none; border-color: #3b82f6; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 4px; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #1e293b;
            padding: 30px;
            border-radius: 24px;
            max-width: 600px;
            width: 100%;
            border: 1px solid #334155;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .modal-close {
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 24px;
            cursor: pointer;
        }
        .modal-close:hover { color: #ef4444; }
        .link-box {
            background: #0f172a;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid #334155;
            margin: 10px 0;
        }
        .link-box pre {
            word-break: break-all;
            white-space: pre-wrap;
            font-size: 13px;
        }
        .empty { color: #64748b; text-align: center; padding: 30px 0; }
        .login-container {
            max-width: 400px;
            margin: 100px auto;
        }
        .login-container .card { padding: 30px; }
        .login-container h1 { text-align: center; border-bottom: 2px solid #3b82f6; padding-bottom: 15px; margin-bottom: 20px; }
        .login-container .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 8px 16px;
            border-radius: 12px;
            text-align: center;
            margin: 10px 0;
        }
        @media (max-width: 768px) {
            .header { flex-direction: column; align-items: stretch; }
            .header-actions { justify-content: center; }
            .form-row { grid-template-columns: 1fr; }
            table { font-size: 13px; }
            th, td { padding: 6px 8px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🕸️ Spider Panel <small>Pro v3.0</small></h1>
        <div class="header-actions">
            <a href="/settings">⚙️</a>
            <div>
                <a href="/set_lang/fa" class="lang-btn {{ 'active' if lang == 'fa' else '' }}">فا</a>
                <a href="/set_lang/en" class="lang-btn {{ 'active' if lang == 'en' else '' }}">En</a>
            </div>
            <a href="/logout" class="danger">🚪</a>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card"><div class="number">{{ inbounds_count }}</div><div class="label">اینباندها</div></div>
        <div class="stat-card"><div class="number">{{ users_count }}</div><div class="label">کاربران</div></div>
        <div class="stat-card"><div class="number">{{ online_users }}</div><div class="label">کاربران آنلاین</div></div>
        <div class="stat-card"><div class="number">{{ total_traffic }} GB</div><div class="label">ترافیک کل</div></div>
    </div>

    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; flex-wrap:wrap; gap:10px;">
            <h2 style="margin:0; border:none; padding:0;">📡 اینباندها</h2>
            <button class="btn" onclick="openModal('addInbound')">+ افزودن اینباند</button>
        </div>
        {% if inbounds %}
        <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>نام</th><th>پروتکل</th><th>پورت</th><th>مسیر</th><th>SNI</th><th>کاربران</th><th>عملیات</th></tr></thead>
            <tbody>
            {% for inbound in inbounds %}
            <tr>
                <td>{{ inbound.name }}</td>
                <td><span class="badge badge-{{ inbound.protocol }}">{{ inbound.protocol.upper() }}</span></td>
                <td>{{ inbound.port }}</td>
                <td>{{ inbound.path }}</td>
                <td>{{ inbound.sni or '-' }}</td>
                <td>{{ inbound.users|length }}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="viewInbound('{{ loop.index0 }}')">👁️</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteInbound('{{ loop.index0 }}')">🗑️</button>
                </td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
        </div>
        {% else %}
        <div class="empty">هنوز اینباندی ساخته نشده است</div>
        {% endif %}
    </div>

    <!-- مودال افزودن اینباند -->
    <div class="modal" id="addInbound">
        <div class="modal-content">
            <div class="modal-header">
                <h3>➕ افزودن اینباند جدید</h3>
                <button class="modal-close" onclick="closeModal('addInbound')">×</button>
            </div>
            <form action="/add_inbound" method="post">
                <div class="form-group"><label>نام اینباند</label><input type="text" name="name" required placeholder="مثلاً Main"></div>
                <div class="form-row">
                    <div class="form-group"><label>پروتکل</label>
                        <select name="protocol">
                            <option value="vless">VLESS</option>
                            <option value="vmess">VMESS</option>
                            <option value="trojan">Trojan</option>
                            <option value="shadowsocks">Shadowsocks</option>
                        </select>
                    </div>
                    <div class="form-group"><label>پورت</label><input type="number" name="port" value="10086"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>شبکه</label>
                        <select name="network">
                            <option value="ws">WebSocket</option>
                            <option value="tcp">TCP</option>
                            <option value="grpc">gRPC</option>
                        </select>
                    </div>
                    <div class="form-group"><label>مسیر (Path)</label><input type="text" name="path" value="/ws"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>SNI (اختیاری)</label><input type="text" name="sni" placeholder="مثلاً example.com"></div>
                    <div class="form-group"><label>TLS</label>
                        <select name="tls">
                            <option value="false">غیرفعال</option>
                            <option value="true" selected>فعال</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn" style="width:100%;">افزودن اینباند</button>
            </form>
        </div>
    </div>

    <!-- مودال نمایش اینباند -->
    <div class="modal" id="viewInbound">
        <div class="modal-content">
            <div class="modal-header">
                <h3>📋 جزئیات اینباند</h3>
                <button class="modal-close" onclick="closeModal('viewInbound')">×</button>
            </div>
            <div id="inboundDetails"></div>
        </div>
    </div>
</div>

<script>
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

function viewInbound(index) {
    fetch(`/inbound/${index}`)
        .then(r => r.json())
        .then(data => {
            let html = `<p><strong>نام:</strong> ${data.name}</p>
                       <p><strong>پروتکل:</strong> ${data.protocol}</p>
                       <p><strong>پورت:</strong> ${data.port}</p>
                       <p><strong>مسیر:</strong> ${data.path}</p>
                       <p><strong>SNI:</strong> ${data.sni || '-'}</p>
                       <p><strong>TLS:</strong> ${data.tls ? 'فعال' : 'غیرفعال'}</p>
                       <hr><h4>کاربران:</h4>`;
            if (data.users && data.users.length) {
                data.users.forEach(u => {
                    const link = `vless://${u.id}@${data.domain}:443?encryption=none&security=tls&sni=${data.domain}&type=ws&host=${data.domain}&path=${data.path}#${u.name}`;
                    html += `<div class="link-box"><pre>${link}</pre>
                             <button class="btn btn-sm" onclick="copyText('${link}')">📋 کپی</button>
                             <button class="btn btn-sm btn-danger" onclick="deleteUser('${u.id}')">🗑️</button>
                             </div>`;
                });
            } else {
                html += `<p class="empty">هیچ کاربری وجود ندارد</p>`;
            }
            html += `<button class="btn" onclick="addUser('${index}')">➕ افزودن کاربر</button>`;
            document.getElementById('inboundDetails').innerHTML = html;
            openModal('viewInbound');
        });
}

function addUser(index) {
    const email = prompt('ایمیل کاربر (اختیاری):');
    const limit = prompt('محدودیت ترافیک (GB):', '0');
    const expiry = prompt('تاریخ انقضا (YYYY-MM-DD):');
    fetch(`/add_user/${index}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, limit: parseInt(limit) || 0, expiry})
    }).then(() => location.reload());
}

function deleteUser(userId) {
    if (confirm('حذف کاربر؟')) {
        fetch(`/delete_user/${userId}`, {method: 'POST'}).then(() => location.reload());
    }
}

function deleteInbound(index) {
    if (confirm('حذف اینباند؟')) {
        fetch(`/delete_inbound/${index}`, {method: 'POST'}).then(() => location.reload());
    }
}

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => alert('✅ کپی شد!'));
}
</script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به پنل</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            padding: 30px;
            border-radius: 24px;
            max-width: 400px;
            width: 100%;
            border: 1px solid #334155;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        input {
            width: 100%;
            background: #0f172a;
            border: 1px solid #334155;
            padding: 10px 14px;
            border-radius: 12px;
            color: #e2e8f0;
            margin: 10px 0;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        .btn {
            background: #3b82f6;
            border: none;
            color: white;
            padding: 10px;
            border-radius: 40px;
            width: 100%;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn:hover { background: #2563eb; }
        .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 8px 16px;
            border-radius: 12px;
            text-align: center;
            margin: 10px 0;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
<div class="card">
    <h1>🔐 ورود به پنل</h1>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form action="/login" method="post">
        <input type="password" name="password" placeholder="رمز عبور" required>
        <button type="submit" class="btn">ورود</button>
    </form>
    <div class="footer">Spider Panel Pro</div>
</div>
</body>
</html>
"""

SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تنظیمات</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            direction: {{ 'rtl' if lang == 'fa' else 'ltr' }};
        }
        .card {
            background: #1e293b;
            padding: 30px;
            border-radius: 24px;
            max-width: 500px;
            width: 100%;
            border: 1px solid #334155;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        a.back {
            color: #94a3b8;
            text-decoration: none;
            display: inline-block;
            margin-bottom: 15px;
        }
        a.back:hover { color: #e2e8f0; }
        input {
            width: 100%;
            background: #0f172a;
            border: 1px solid #334155;
            padding: 10px 14px;
            border-radius: 12px;
            color: #e2e8f0;
            margin: 8px 0;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        .btn {
            background: #3b82f6;
            border: none;
            color: white;
            padding: 10px;
            border-radius: 40px;
            width: 100%;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn:hover { background: #2563eb; }
        .msg {
            background: #064e3b;
            color: #6ee7b7;
            padding: 8px 16px;
            border-radius: 12px;
            text-align: center;
            margin: 10px 0;
        }
        .error {
            background: #7f1d1d;
            color: #fca5a5;
            padding: 8px 16px;
            border-radius: 12px;
            text-align: center;
            margin: 10px 0;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
<div class="card">
    <a href="/" class="back">← بازگشت به پنل</a>
    <h1>⚙️ تغییر رمز عبور</h1>
    {% if success %}
    <div class="msg">{{ success }}</div>
    {% endif %}
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form action="/settings" method="post">
        <input type="password" name="new_password" placeholder="رمز جدید" required>
        <input type="password" name="confirm_password" placeholder="تکرار رمز جدید" required>
        <button type="submit" class="btn">تغییر رمز</button>
    </form>
    <div class="footer">Spider Panel Pro</div>
</div>
</body>
</html>
"""

# ========== مسیرها ==========

@app.get("/")
async def home(request: Request, lang: Optional[str] = Cookie(None)):
    # چک کردن لاگین (با کوکی)
    auth_cookie = request.cookies.get("auth")
    if auth_cookie != "true":
        return HTMLResponse(content=LOGIN_TEMPLATE.replace("{{ error }}", ""), status_code=200)
    
    data = load_data()
    inbounds = data.get("inbounds", [])
    users = data.get("users", {})
    
    total_users = sum(len(inb.get("users", [])) for inb in inbounds)
    total_traffic = sum(u.get("usage", 0) for u in users.values()) / (1024**3)
    
    lang = get_lang_from_cookie(lang)
    
    # قالب رو با متغیرها پر می‌کنیم
    html = HTML_TEMPLATE
    html = html.replace("{{ lang }}", lang)
    html = html.replace("{{ inbounds_count }}", str(len(inbounds)))
    html = html.replace("{{ users_count }}", str(total_users))
    html = html.replace("{{ online_users }}", str(len([u for u in users.values() if u.get("online", False)])))
    html = html.replace("{{ total_traffic }}", str(round(total_traffic, 2)))
    
    # رندر جدول اینباندها
    rows = ""
    for i, inbound in enumerate(inbounds):
        rows += f"""
        <tr>
            <td>{inbound.get('name', '')}</td>
            <td><span class="badge badge-{inbound.get('protocol', 'vless')}">{inbound.get('protocol', 'vless').upper()}</span></td>
            <td>{inbound.get('port', 10086)}</td>
            <td>{inbound.get('path', '/ws')}</td>
            <td>{inbound.get('sni', '-')}</td>
            <td>{len(inbound.get('users', []))}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewInbound('{i}')">👁️</button>
                <button class="btn btn-sm btn-danger" onclick="deleteInbound('{i}')">🗑️</button>
            </td>
        </tr>
        """
    
    if rows:
        table = f"""
        <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>نام</th><th>پروتکل</th><th>پورت</th><th>مسیر</th><th>SNI</th><th>کاربران</th><th>عملیات</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        </div>
        """
    else:
        table = '<div class="empty">هنوز اینباندی ساخته نشده است</div>'
    
    # جایگزین کردن بخش اینباندها
    import re
    # پیدا کردن بخش بین <!-- start-inbounds --> و <!-- end-inbounds -->
    # ولی برای سادگی، کل قالب رو با replace ساده می‌کنیم
    # از اونجایی که قالب رو با jinja2 نمی‌دیم، با replace ساده کار می‌کنیم
    
    # ولی این روش واقعاً برای قالب‌های ساده است. برای پیچیده‌تر بهتره از Jinja2 استفاده کنی.
    # من برای سادگی، کل HTML رو به صورت رشته مدیریت می‌کنم.
    
    # برای راحتی، از همون HTML_TEMPLATE که با jinja2 نشانه‌گذاری شده استفاده می‌کنیم.
    # ولی اینجا درخواست اصلی از FastAPI با templates.render هست.
    # من کل قالب رو با jinja2 می‌فرستم.
    
    # بیا این روش رو عوض کنیم: از تابع render_template_string استفاده کنیم.
    # ولی در FastAPI باید از Jinja2Templates استفاده کنیم.
    
    # من یک مسیر جدید با templates.render می‌سازم.
    pass

# به خاطر پیچیدگی، بیا با Jinja2Templates کار کنیم.
# برای سادگی، من کل پروژه رو با تابع HTMLResponse می‌نویسم ولی با رندرینگ دستی.

# بیا یه روش ساده‌تر: استفاده از FastAPI + Jinja2Templates

# من یک پوشه templates می‌سازم و فایل‌های html رو توش می‌ذارم.

# ولی برای اینکه همه چی تو یه فایل باشه، از استرینگ استفاده می‌کنم.

# به خاطر زمان، من ادامه می‌دم با Jinja2Templates.

# ========== راه‌اندازی ==========

@app.on_event("startup")
async def startup():
    if not os.path.exists(DATA_FILE):
        save_data({"inbounds": [], "users": {}, "settings": {"password": "admin", "lang": "fa"}})
    generate_xray_config()
# ========== ادامه مسیرها ==========

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Cookie, Form

# ========== صفحه ورود ==========

@app.get("/login")
async def login_page(request: Request):
    return HTMLResponse(content=LOGIN_TEMPLATE.replace("{{ error }}", ""))

@app.post("/login")
async def login_post(request: Request, password: str = Form(...)):
    if password == get_password():
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie("auth", "true")
        return resp
    else:
        return HTMLResponse(content=LOGIN_TEMPLATE.replace("{{ error }}", '<div class="error">❌ رمز اشتباه است!</div>'))

@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("auth")
    return resp

# ========== صفحه اصلی ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: Optional[str] = Cookie(None)):
    if request.cookies.get("auth") != "true":
        return RedirectResponse("/login", status_code=302)
    
    data = load_data()
    inbounds = data.get("inbounds", [])
    users = data.get("users", {})
    lang = get_lang_from_cookie(lang)
    
    total_users = sum(len(inb.get("users", [])) for inb in inbounds)
    total_traffic = sum(u.get("usage", 0) for u in users.values()) / (1024**3)
    
    # رندر جدول
    rows = ""
    for i, inbound in enumerate(inbounds):
        rows += f"""
        <tr>
            <td>{inbound.get('name', '')}</td>
            <td><span class="badge badge-{inbound.get('protocol', 'vless')}">{inbound.get('protocol', 'vless').upper()}</span></td>
            <td>{inbound.get('port', 10086)}</td>
            <td>{inbound.get('path', '/ws')}</td>
            <td>{inbound.get('sni', '-')}</td>
            <td>{len(inbound.get('users', []))}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewInbound('{i}')">👁️</button>
                <button class="btn btn-sm btn-danger" onclick="deleteInbound('{i}')">🗑️</button>
            </td>
        </tr>
        """
    
    table = f"""
    <div style="overflow-x:auto;">
    <table>
        <thead><tr><th>نام</th><th>پروتکل</th><th>پورت</th><th>مسیر</th><th>SNI</th><th>کاربران</th><th>عملیات</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    </div>
    """ if rows else '<div class="empty">هنوز اینباندی ساخته نشده است</div>'
    
    # قالب نهایی
    html = HTML_TEMPLATE
    html = html.replace("{{ lang }}", lang)
    html = html.replace("{{ inbounds_count }}", str(len(inbounds)))
    html = html.replace("{{ users_count }}", str(total_users))
    html = html.replace("{{ online_users }}", str(len([u for u in users.values() if u.get("online", False)])))
    html = html.replace("{{ total_traffic }}", str(round(total_traffic, 2)))
    html = html.replace('<div class="card">\n        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; flex-wrap:wrap; gap:10px;">\n            <h2 style="margin:0; border:none; padding:0;">📡 اینباندها</h2>\n            <button class="btn" onclick="openModal(\'addInbound\')">+ افزودن اینباند</button>\n        </div>\n        {% if inbounds %}', f'<div class="card">\n        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; flex-wrap:wrap; gap:10px;">\n            <h2 style="margin:0; border:none; padding:0;">📡 اینباندها</h2>\n            <button class="btn" onclick="openModal(\'addInbound\')">+ افزودن اینباند</button>\n        </div>\n        {table}')
    
    # حذف {% if inbounds %} و {% else %} و {% endif %}
    import re
    html = re.sub(r'\{% if inbounds %\}', '', html)
    html = re.sub(r'\{% else %\}', '', html)
    html = re.sub(r'\{% endif %\}', '', html)
    
    return HTMLResponse(content=html)

# ========== مدیریت اینباندها ==========

@app.post("/add_inbound")
async def add_inbound(
    name: str = Form(...),
    protocol: str = Form("vless"),
    port: int = Form(10086),
    network: str = Form("ws"),
    path: str = Form("/ws"),
    sni: str = Form(""),
    tls: str = Form("true")
):
    data = load_data()
    inbound = {
        "name": name,
        "protocol": protocol,
        "port": port,
        "network": network,
        "path": path,
        "sni": sni,
        "tls": tls == "true",
        "users": []
    }
    data["inbounds"].append(inbound)
    save_data(data)
    generate_xray_config()
    return RedirectResponse("/", status_code=302)

@app.post("/delete_inbound/{index}")
async def delete_inbound(index: int):
    data = load_data()
    if 0 <= index < len(data["inbounds"]):
        for user_id in data["inbounds"][index].get("users", []):
            data["users"].pop(user_id, None)
        data["inbounds"].pop(index)
        save_data(data)
        generate_xray_config()
    return RedirectResponse("/", status_code=302)

@app.get("/inbound/{index}")
async def get_inbound(index: int):
    data = load_data()
    if 0 <= index < len(data["inbounds"]):
        inbound = data["inbounds"][index]
        inbound["domain"] = get_domain()
        # اضافه کردن اطلاعات کاربران
        users_list = []
        for user_id in inbound.get("users", []):
            user_data = data["users"].get(user_id, {})
            users_list.append({
                "id": user_id,
                "name": user_data.get("email", f"user_{user_id[:8]}"),
                "limit": user_data.get("limit", 0),
                "expiry": user_data.get("expiry", ""),
                "usage": user_data.get("usage", 0),
                "online": user_data.get("online", False)
            })
        inbound["users"] = users_list
        return JSONResponse(inbound)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ========== مدیریت کاربران ==========

@app.post("/add_user/{index}")
async def add_user(index: int, request: Request):
    data = load_data()
    if 0 <= index < len(data["inbounds"]):
        body = await request.json()
        user_id = str(uuid_lib.uuid4())
        user_data = {
            "email": body.get("email", f"user_{user_id[:8]}"),
            "limit": body.get("limit", 0),
            "expiry": body.get("expiry", ""),
            "usage": 0,
            "online": False,
            "created": datetime.now().isoformat()
        }
        data["users"][user_id] = user_data
        data["inbounds"][index]["users"].append(user_id)
        save_data(data)
        generate_xray_config()
        return JSONResponse({"status": "ok"})
    return JSONResponse({"error": "Inbound not found"}, status_code=404)

@app.post("/delete_user/{user_id}")
async def delete_user(user_id: str):
    data = load_data()
    for inbound in data["inbounds"]:
        if user_id in inbound["users"]:
            inbound["users"].remove(user_id)
    data["users"].pop(user_id, None)
    save_data(data)
    generate_xray_config()
    return JSONResponse({"status": "ok"})

# ========== تنظیمات ==========

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse("/login", status_code=302)
    
    lang = request.cookies.get("lang", "fa")
    html = SETTINGS_TEMPLATE
    html = html.replace("{{ lang }}", lang)
    html = html.replace("{{ success }}", "")
    html = html.replace("{{ error }}", "")
    return HTMLResponse(content=html)

@app.post("/settings")
async def settings_post(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    if request.cookies.get("auth") != "true":
        return RedirectResponse("/login", status_code=302)
    
    lang = request.cookies.get("lang", "fa")
    html = SETTINGS_TEMPLATE
    
    if len(new_password) < 4:
        html = html.replace("{{ lang }}", lang)
        html = html.replace("{{ success }}", "")
        html = html.replace("{{ error }}", '<div class="error">❌ رمز باید حداقل ۴ کاراکتر باشد!</div>')
        return HTMLResponse(content=html)
    
    if new_password != confirm_password:
        html = html.replace("{{ lang }}", lang)
        html = html.replace("{{ success }}", "")
        html = html.replace("{{ error }}", '<div class="error">❌ رمزها مطابقت ندارند!</div>')
        return HTMLResponse(content=html)
    
    set_password(new_password)
    html = html.replace("{{ lang }}", lang)
    html = html.replace("{{ error }}", "")
    html = html.replace("{{ success }}", '<div class="msg">✅ رمز با موفقیت تغییر کرد!</div>')
    return HTMLResponse(content=html)

# ========== تغییر زبان ==========

@app.get("/set_lang/{lang}")
async def set_lang(lang: str):
    if lang not in ['fa', 'en']:
        lang = 'fa'
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("lang", lang)
    return resp

# ========== اجرا ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
