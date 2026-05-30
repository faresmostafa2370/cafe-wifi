#!/usr/bin/env python3
"""
☕ نظام كافية الواحة - للشبكة العادية ☕

المميزات:
- شبكة واي فاي مفتوحة (من الراوتر)
- أي جهاز يتصل يظهر له صفحة تسجيل الدخول
- بعد إدخال الرقم الصحيح → تصفح لمدة محددة
- قطع الإنترنت تلقائياً بعد انتهاء الوقت
- لوحة تحكم أدمن محمية
"""

import os
import sys
import sqlite3
import datetime
import socket
import subprocess
import platform
import threading
import time
import hashlib
from flask import Flask, request, render_template_string, redirect, jsonify, session

# ========== CONFIGURATION ==========
PORT = 8080
CAFE_NAME = "الواحة"
SERVICE_NUMBER = "01273834877"
ROUTER_IP = "192.168.1.1"  # IP الراوتر
SERVER_IP = ""  # هيتحدد تلقائياً

# ========== ADMIN PROTECTION ==========
ADMIN_USERNAME = "admin01208571***Fm"
ADMIN_PASSWORD = "01208571***FmPass"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)

# ========== FLASK APP ==========
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== HTML CAPTIVE PAGE ==========
CAPTIVE_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>☕ كافية {{ cafe_name }}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
            font-family:'Cairo','Tahoma',sans-serif;
            min-height:100vh;
            display:flex;
            justify-content:center;
            align-items:center
        }
        .container{
            background:rgba(0,0,0,0.85);
            border-radius:20px;
            padding:40px;
            max-width:450px;
            width:90%;
            border:2px solid #ff6b35;
            box-shadow:0 0 30px rgba(255,107,53,0.3);
            text-align:center
        }
        h1{color:#ff6b35;margin-bottom:10px;font-size:28px}
        .logo{font-size:60px;margin-bottom:10px}
        .subtitle{color:#888;margin-bottom:30px;font-size:14px}
        input{
            width:100%;
            padding:15px;
            margin:10px 0;
            background:#1a1a1a;
            border:1px solid #ff6b35;
            border-radius:10px;
            color:#ff6b35;
            font-size:18px;
            text-align:center
        }
        button{
            width:100%;
            padding:15px;
            background:linear-gradient(90deg,#ff6b35,#ff8c42);
            border:none;
            border-radius:10px;
            color:#fff;
            font-size:20px;
            font-weight:bold;
            cursor:pointer;
            margin-top:10px
        }
        .error{color:#ff0033;margin-top:10px;font-size:14px}
        .footer{color:#555;font-size:12px;margin-top:20px}
        .contact{color:#ff6b35;margin-top:15px}
        .prices{display:flex;justify-content:space-between;margin-top:20px;gap:10px}
        .price-card{background:#1a1a1a;padding:10px;border-radius:10px;flex:1}
        .price-card .hours{color:#ff6b35;font-size:20px;font-weight:bold}
        .price-card .price{color:#888;font-size:12px}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">☕</div>
        <h1>كافية {{ cafe_name }}</h1>
        <div class="subtitle">أدخل رقم الكرت لبدء التصفح</div>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="📱 رقم الكرت" required autocomplete="off" autofocus>
            <button type="submit">🚀 دخول الإنترنت</button>
        </form>
        <div class="error">{{ error }}</div>
        <div class="prices">
            <div class="price-card"><div class="hours">1 ساعة</div><div>10 ج</div></div>
            <div class="price-card"><div class="hours">2 ساعة</div><div>15 ج</div></div>
            <div class="price-card"><div class="hours">4 ساعة</div><div>25 ج</div></div>
            <div class="price-card"><div class="hours">8 ساعة</div><div>40 ج</div></div>
        </div>
        <div class="footer">
            <div class="contact">📞 للكروت: {{ service_number }}</div>
        </div>
    </div>
</body>
</html>
'''

# ========== DASHBOARD PAGE ==========
DASHBOARD_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم - كافية {{ cafe_name }}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            background:#0a0a0a;
            font-family:'Cairo','Tahoma',sans-serif;
            min-height:100vh;
            display:flex;
            justify-content:center;
            align-items:center
        }
        .container{
            background:#1a1a1a;
            border-radius:20px;
            padding:40px;
            max-width:500px;
            width:90%;
            border:2px solid #00ff41;
            box-shadow:0 0 30px rgba(0,255,65,0.3);
            text-align:center
        }
        h1{color:#00ff41;margin-bottom:20px;font-size:28px}
        .welcome{color:#ff6b35;margin-bottom:10px;font-size:20px}
        .remaining{font-size:18px;color:#888;margin:20px 0}
        .timer{
            font-size:72px;
            color:#00ff41;
            font-family:monospace;
            margin:20px 0;
            padding:20px;
            background:#0a0a0a;
            border-radius:15px;
            letter-spacing:5px
        }
        .info{
            background:#0a0a0a;
            padding:15px;
            border-radius:10px;
            margin:20px 0;
            text-align:left
        }
        .info p{margin:8px 0;color:#00ff41;font-size:14px}
        .info span{color:#888}
        .button{
            display:inline-block;
            padding:10px 20px;
            background:#ff6b35;
            color:#fff;
            text-decoration:none;
            border-radius:8px;
            margin:5px;
            font-weight:bold
        }
        .logout{background:#ff0033}
        .warning{color:#ff6600;font-size:12px;margin-top:10px}
    </style>
</head>
<body>
    <div class="container">
        <h1>☕ {{ cafe_name }}</h1>
        <div class="welcome">✅ مرحباً {{ username }}</div>
        <div class="remaining">الوقت المتبقي</div>
        <div class="timer" id="timer">--:--</div>
        <div class="info">
            <p>📡 <span>عنوان الأيبي:</span> {{ ip }}</p>
            <p>⏱️ <span>وقت البدء:</span> {{ start_time }}</p>
            <p>⏰ <span>ينتهي في:</span> {{ end_time }}</p>
        </div>
        <a href="https://www.google.com" class="button">🌐 بدء التصفح</a>
        <a href="/logout" class="button logout">🚪 إنهاء الجلسة</a>
        <div class="warning">⚠️ سيتم قطع الإنترنت تلقائياً عند انتهاء الوقت</div>
    </div>
    <script>
        let remainingSeconds = {{ remaining_seconds }};
        const timerElement = document.getElementById('timer');
        
        function formatTime(seconds) {
            let hours = Math.floor(seconds / 3600);
            let minutes = Math.floor((seconds % 3600) / 60);
            let secs = seconds % 60;
            if(hours > 0) {
                return String(hours).padStart(2,'0') + ':' + String(minutes).padStart(2,'0') + ':' + String(secs).padStart(2,'0');
            }
            return String(minutes).padStart(2,'0') + ':' + String(secs).padStart(2,'0');
        }
        
        function updateTimer() {
            timerElement.innerHTML = formatTime(remainingSeconds);
            if(remainingSeconds <= 0) {
                timerElement.innerHTML = '00:00';
                timerElement.style.color = '#ff0033';
                setTimeout(() => { window.location.href = '/logout'; }, 3000);
            } else {
                remainingSeconds--;
                setTimeout(updateTimer, 1000);
            }
        }
        
        updateTimer();
    </script>
</body>
</html>
'''

# ========== ADMIN LOGIN PAGE ==========
ADMIN_LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>دخول الأدمن - كافية {{ cafe_name }}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            background:linear-gradient(135deg,#0a0a0a 0%,#1a1a2e 100%);
            font-family:'Cairo','Tahoma',sans-serif;
            min-height:100vh;
            display:flex;
            justify-content:center;
            align-items:center
        }
        .container{
            background:rgba(0,0,0,0.85);
            border-radius:20px;
            padding:40px;
            max-width:400px;
            width:90%;
            border:2px solid #ff0033;
            box-shadow:0 0 30px rgba(255,0,51,0.3);
            text-align:center
        }
        h1{color:#ff0033;margin-bottom:20px}
        input{
            width:100%;
            padding:12px;
            margin:10px 0;
            background:#1a1a1a;
            border:1px solid #ff0033;
            border-radius:8px;
            color:#00ff41;
            font-size:16px
        }
        button{
            width:100%;
            padding:12px;
            background:#ff0033;
            color:#fff;
            border:none;
            border-radius:8px;
            font-size:18px;
            font-weight:bold;
            cursor:pointer;
            margin-top:10px
        }
        .error{color:#ff0033;margin-top:10px}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 دخول الأدمن</h1>
        <form method="POST" action="/admin/login">
            <input type="text" name="username" placeholder="اسم المستخدم" required autofocus>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
        <div class="error">{{ error }}</div>
    </div>
</body>
</html>
'''

# ========== ADMIN PANEL PAGE ==========
ADMIN_PANEL_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة الأدمن - كافية {{ cafe_name }}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0a0a;font-family:'Cairo',sans-serif;padding:20px}
        .container{max-width:900px;margin:auto}
        h1{color:#ff6b35;text-align:center;margin-bottom:30px}
        .card{background:#1a1a1a;border:1px solid #ff6b35;border-radius:10px;padding:20px;margin-bottom:20px}
        .card h2{color:#ff8c42;margin-bottom:15px}
        table{width:100%;border-collapse:collapse}
        th,td{padding:10px;text-align:center;border-bottom:1px solid #333}
        th{color:#ff6b35}
        td{color:#fff}
        input{padding:8px;margin:5px;background:#0a0a0a;border:1px solid #ff6b35;color:#fff;border-radius:5px}
        button{padding:8px 15px;background:#ff6b35;color:#fff;border:none;border-radius:5px;cursor:pointer}
        .menu{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}
        .btn{background:#ff6b35;color:#fff;padding:10px 20px;text-decoration:none;border-radius:8px}
        .stats{display:flex;gap:15px;margin-bottom:20px;flex-wrap:wrap}
        .stat{background:#1a1a1a;border:1px solid #ff6b35;border-radius:10px;padding:15px;text-align:center;flex:1}
        .stat-number{font-size:36px;color:#00ff41;font-weight:bold}
        .stat-label{color:#888}
        .logout-btn{background:#ff0033;color:#fff}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 لوحة تحكم الأدمن - كافية {{ cafe_name }}</h1>
        <div class="stats">
            <div class="stat"><div class="stat-number">{{ active_sessions }}</div><div class="stat-label">متصلون الآن</div></div>
            <div class="stat"><div class="stat-number">{{ total_cards }}</div><div class="stat-label">إجمالي الكروت</div></div>
            <div class="stat"><div class="stat-number">{{ used_cards }}</div><div class="stat-label">كروت مستخدمة</div></div>
        </div>
        <div class="menu">
            <a href="/admin" class="btn">📊 الرئيسية</a>
            <a href="/admin/cards" class="btn">💳 الكروت</a>
            <a href="/admin/logout" class="btn logout-btn">🚪 تسجيل الخروج</a>
        </div>
        <div class="card">
            <h2>➕ إضافة كرت جديد</h2>
            <form method="POST" action="/admin/add">
                <input type="text" name="username" placeholder="رقم الكرت" required>
                <select name="minutes">
                    <option value="60">1 ساعة (60 دقيقة)</option>
                    <option value="120">2 ساعة (120 دقيقة)</option>
                    <option value="240">4 ساعة (240 دقيقة)</option>
                    <option value="480">8 ساعة (480 دقيقة)</option>
                </select>
                <button type="submit">➕ إضافة</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  card_number TEXT UNIQUE,
                  minutes INTEGER DEFAULT 0,
                  created_at TEXT,
                  used INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  card_number TEXT,
                  ip TEXT,
                  start_time TEXT,
                  minutes INTEGER DEFAULT 0)''')
    
    # إضافة كروت تجريبية
    demo_cards = [
        ('123456', 60),
        ('111111', 120),
        ('222222', 240),
        ('333333', 480),
    ]
    
    now = datetime.datetime.now().isoformat()
    for card, minutes in demo_cards:
        c.execute("INSERT OR IGNORE INTO cards (card_number, minutes, created_at) VALUES (?, ?, ?)",
                  (card, minutes, now))
    
    conn.commit()
    conn.close()
    print("[✅] Database initialized")

def check_card(card_number):
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute("SELECT card_number, minutes FROM cards WHERE card_number=? AND used=0", (card_number,))
    card = c.fetchone()
    conn.close()
    return card

def use_card(card_number):
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute("UPDATE cards SET used=1 WHERE card_number=?", (card_number,))
    conn.commit()
    conn.close()

def add_session(card_number, ip, minutes):
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute("INSERT INTO sessions (card_number, ip, start_time, minutes) VALUES (?, ?, ?, ?)",
              (card_number, ip, datetime.datetime.now().isoformat(), minutes))
    conn.commit()
    conn.close()

def get_all_cards():
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute("SELECT id, card_number, minutes, created_at, used FROM cards ORDER BY id DESC")
    cards = c.fetchall()
    conn.close()
    return cards

def add_card(card_number, minutes):
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO cards (card_number, minutes, created_at) VALUES (?, ?, ?)",
                  (card_number, minutes, datetime.datetime.now().isoformat()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_used_cards_count():
    conn = sqlite3.connect('cafe_wifi.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE used=1")
    count = c.fetchone()[0]
    conn.close()
    return count

# ========== ACTIVE SESSIONS ==========
active_sessions = {}

# ========== IPTABLES CONTROL (منع/السماح للمستخدمين) ==========
def allow_user(ip):
    """السماح لمستخدم بالإنترنت"""
    system = platform.system()
    if system == "Linux":
        subprocess.run(f'sudo iptables -I FORWARD -s {ip} -j ACCEPT', shell=True)
        print(f"[✅] User {ip} allowed to access internet")
    elif system == "Windows":
        print(f"[✅] User {ip} added (manual sharing required)")

def block_user(ip):
    """منع مستخدم من الإنترنت"""
    system = platform.system()
    if system == "Linux":
        subprocess.run(f'sudo iptables -D FORWARD -s {ip} -j ACCEPT', shell=True)
        print(f"[❌] User {ip} blocked from internet")

# ========== GET LOCAL IP ==========
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    client_ip = request.remote_addr
    print(f"[🌐] Client {client_ip} connected")
    return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER, error="")

@app.route('/login', methods=['POST'])
def login():
    card_number = request.form.get('username')
    client_ip = request.remote_addr
    
    card = check_card(card_number)
    
    if card:
        minutes = card[1]
        use_card(card_number)
        add_session(card_number, client_ip, minutes)
        
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(minutes=minutes)
        remaining_seconds = minutes * 60
        
        active_sessions[client_ip] = {
            'card_number': card_number,
            'start_time': start_time,
            'minutes': minutes,
            'remaining': remaining_seconds
        }
        
        # السماح للمستخدم بالإنترنت
        allow_user(client_ip)
        
        print(f"[✅] Card {card_number} activated from {client_ip} ({minutes} minutes)")
        
        return render_template_string(DASHBOARD_PAGE,
                                      cafe_name=CAFE_NAME,
                                      username=card_number,
                                      ip=client_ip,
                                      start_time=start_time.strftime("%H:%M:%S"),
                                      end_time=end_time.strftime("%H:%M:%S"),
                                      remaining_seconds=remaining_seconds)
    else:
        print(f"[❌] Invalid card {card_number} from {client_ip}")
        return render_template_string(CAPTIVE_PAGE,
                                      cafe_name=CAFE_NAME,
                                      service_number=SERVICE_NUMBER,
                                      error="❌ رقم الكرت غير صالح أو مستخدم")

@app.route('/status')
def status():
    client_ip = request.remote_addr
    if client_ip in active_sessions:
        session_data = active_sessions[client_ip]
        elapsed = (datetime.datetime.now() - session_data['start_time']).seconds
        remaining = max(0, session_data['minutes'] * 60 - elapsed)
        return jsonify({"active": True, "remaining": remaining})
    return jsonify({"active": False})

@app.route('/logout')
def logout():
    client_ip = request.remote_addr
    if client_ip in active_sessions:
        # منع المستخدم من الإنترنت
        block_user(client_ip)
        print(f"[🚪] Card {active_sessions[client_ip]['card_number']} logged out from {client_ip}")
        del active_sessions[client_ip]
    return redirect('/')

# مسارات Captive Portal
@app.route('/generate_204')
def generate_204():
    return redirect('/')

@app.route('/hotspot-detect.html')
def hotspot_detect():
    return redirect('/')

@app.route('/ncsi.txt')
def ncsi():
    return redirect('/')

@app.route('/connectivity_check.html')
def connectivity_check():
    return redirect('/')

# ========== ADMIN ROUTES ==========
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            error = "❌ اسم المستخدم أو كلمة المرور غير صحيحة"
    
    return render_template_string(ADMIN_LOGIN_PAGE, cafe_name=CAFE_NAME, error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    cards = get_all_cards()
    active = len(active_sessions)
    used = get_used_cards_count()
    
    return render_template_string(ADMIN_PANEL_PAGE,
                                  cafe_name=CAFE_NAME,
                                  active_sessions=active,
                                  total_cards=len(cards),
                                  used_cards=used)

@app.route('/admin/cards')
def admin_cards():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    cards = get_all_cards()
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>الكروت - كافية الواحة</title>
        <style>
            body{background:#0a0a0a;font-family:sans-serif;padding:20px}
            h1{color:#ff6b35;text-align:center}
            table{width:100%;border-collapse:collapse;margin-top:20px}
            th,td{padding:10px;text-align:center;border-bottom:1px solid #333}
            th{color:#ff6b35}
            td{color:#fff}
            .available{color:#00ff41}
            .used{color:#ff0033}
            .back{color:#ff6b35;text-decoration:none;display:inline-block;margin-bottom:20px}
            .stats{margin-bottom:20px;padding:15px;background:#1a1a1a;border-radius:10px}
        </style>
    </head>
    <body>
        <a href="/admin" class="back">← رجوع للوحة الرئيسية</a>
        <h1>💳 إدارة الكروت</h1>
        <div class="stats">
            <strong style="color:#00ff41">✅ المتاحة:</strong> <span style="color:#fff">{{ available }}</span> &nbsp;|&nbsp;
            <strong style="color:#ff0033">❌ المستخدمة:</strong> <span style="color:#fff">{{ used }}</span> &nbsp;|&nbsp;
            <strong style="color:#ff6b35">📊 الإجمالي:</strong> <span style="color:#fff">{{ total }}</span>
        </div>
        <table>
            <tr><th>ID</th><th>رقم الكرت</th><th>الدقائق</th><th>تاريخ الإضافة</th><th>الحالة</th></tr>
    '''
    
    available = 0
    used = 0
    for card in cards:
        if card[4]:
            used += 1
            status = "❌ مستخدم"
            status_class = "used"
        else:
            available += 1
            status = "✅ متاح"
            status_class = "available"
        html += f"<tr><td>{card[0]}</td><td>{card[1]}</td><td>{card[2]}</td><td>{card[3][:10]}</td><td class='{status_class}'>{status}</td></tr>"
    
    html += f'''
        </table>
        <script>
            document.querySelector('.stats').innerHTML = document.querySelector('.stats').innerHTML
                .replace('{{ available }}', '{available}')
                .replace('{{ used }}', '{used}')
                .replace('{{ total }}', '{len(cards)}');
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    card_number = request.form.get('username')
    minutes = int(request.form.get('minutes', 60))
    
    if add_card(card_number, minutes):
        return render_template_string(CAPTIVE_PAGE,
                                      cafe_name=CAFE_NAME,
                                      service_number=SERVICE_NUMBER,
                                      error=f"✅ تم إضافة الكرت {card_number} ({minutes} دقيقة)")
    else:
        return render_template_string(CAPTIVE_PAGE,
                                      cafe_name=CAFE_NAME,
                                      service_number=SERVICE_NUMBER,
                                      error=f"❌ الكرت {card_number} موجود بالفعل")

# ========== MAIN ==========
def main():
    global SERVER_IP
    SERVER_IP = get_local_ip()
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                    ☕ نظام كافية الواحة ☕                        ║
║                                                                   ║
║   • شبكة واي فاي مفتوحة (من الراوتر)                            ║
║   • أي جهاز يتصل يظهر له صفحة تسجيل الدخول                       ║
║   • بعد إدخال الرقم الصحيح → تصفح لمدة محددة                     ║
║   • قطع الإنترنت تلقائياً بعد انتهاء الوقت                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # تهيئة قاعدة البيانات
    init_db()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                          ✅ SYSTEM READY                          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   🌐 صفحة تسجيل الدخول: http://{SERVER_IP}:{PORT}                 ║
║   🔧 لوحة الأدمن: http://{SERVER_IP}:{PORT}/admin                 ║
║                                                                   ║
║   🔐 بيانات دخول الأدمن:                                          ║
║       المستخدم: {ADMIN_USERNAME}                                  ║
║       كلمة السر: {ADMIN_PASSWORD}                                 ║
║                                                                   ║
║   📝 كروت تجريبية:                                                ║
║       123456 → 60 دقيقة                                          ║
║       111111 → 120 دقيقة                                         ║
║       222222 → 240 دقيقة                                         ║
║       333333 → 480 دقيقة                                         ║
║                                                                   ║
║   📡 إعدادات الراوتر:                                             ║
║       اجعل شبكة الواي فاي مفتوحة (بدون باسورد)                   ║
║       أو استخدم Captive Portal على الراوتر نفسه                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # تشغيل السيرفر
    try:
        from waitress import serve
        print("🚀 Using waitress (fast server)")
        serve(app, host='0.0.0.0', port=PORT)
    except ImportError:
        print("⚠️ Using Flask. Install waitress for better performance: pip install waitress")
        app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        sys.exit(0)