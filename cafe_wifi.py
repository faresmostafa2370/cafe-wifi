#!/usr/bin/env python3
"""
☕ نظام كافية الواحة - النسخة المتكاملة ☕

المميزات:
- تفعيل بالبيانات (ميجابايت)
- حماية من التخمين (بعد 5 محاولات خاطئة)
- إنشاء كروت جماعية (كمية مرة واحدة)
- صفحة مستخدم جذابة
- لوحة تحكم أدمن متكاملة
"""

import os
import sys
import sqlite3
import datetime
import socket
import hashlib
import random
import string
from flask import Flask, request, redirect, jsonify, session, render_template_string

# ========== CONFIGURATION ==========
PORT = int(os.environ.get("PORT", 8080))
CAFE_NAME = "الواحة"
SERVICE_NUMBER = "01273834877"

# إعدادات الحماية من التخمين
MAX_FAILED_ATTEMPTS = 5
BLOCK_TIME_MINUTES = 10

# قاعدة البيانات
DB_PATH = os.environ.get("DB_PATH", "/tmp/cafe_wifi.db")

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
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            font-family: 'Cairo', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 40px;
            max-width: 480px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
        }
        .logo { font-size: 70px; margin-bottom: 10px; animation: bounce 2s ease infinite; }
        @keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        h1 { color: #fff; font-size: 32px; margin-bottom: 10px; }
        .subtitle { color: rgba(255, 255, 255, 0.7); margin-bottom: 30px; font-size: 14px; }
        .card-input { position: relative; margin: 25px 0; }
        .card-input input {
            width: 100%;
            padding: 18px;
            background: rgba(255, 255, 255, 0.15);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            color: #fff;
            font-size: 18px;
            text-align: center;
            letter-spacing: 2px;
            font-family: monospace;
        }
        .card-input input:focus { outline: none; border-color: #ff6b35; background: rgba(255, 255, 255, 0.25); }
        button {
            width: 100%;
            padding: 18px;
            background: linear-gradient(90deg, #ff6b35, #ff8c42);
            border: none;
            border-radius: 15px;
            color: #fff;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(255, 107, 53, 0.3); }
        .error { color: #ff6b6b; margin-top: 15px; background: rgba(255, 0, 0, 0.1); padding: 10px; border-radius: 10px; }
        .warning { color: #ffaa44; margin-top: 15px; background: rgba(255, 170, 68, 0.1); padding: 10px; border-radius: 10px; }
        .prices { display: flex; gap: 12px; margin: 30px 0 20px; flex-wrap: wrap; }
        .price-card { background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 12px; flex: 1; text-align: center; }
        .price-card .hours { color: #ff8c42; font-size: 18px; font-weight: bold; }
        .footer { color: rgba(255, 255, 255, 0.5); font-size: 12px; margin-top: 20px; }
        .contact { color: #ff8c42; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">☕</div>
        <h1>كافية {{ cafe_name }}</h1>
        <div class="subtitle">أدخل رقم الكرت لبدء التصفح</div>
        <form method="POST" action="/login">
            <div class="card-input">
                <input type="text" name="username" placeholder="•••• •••• •••• ••••" required autofocus>
            </div>
            <button type="submit">🚀 دخول الإنترنت</button>
        </form>
        <div class="error">{{ error }}</div>
        <div class="warning">{{ warning }}</div>
        <div class="prices">
            <div class="price-card"><div class="hours">500 ميجابايت</div><div>10 ج</div></div>
            <div class="price-card"><div class="hours">1 جيجابايت</div><div>15 ج</div></div>
            <div class="price-card"><div class="hours">2 جيجابايت</div><div>25 ج</div></div>
            <div class="price-card"><div class="hours">4 جيجابايت</div><div>40 ج</div></div>
        </div>
        <div class="footer">
            <div class="contact">📞 للكروت: {{ service_number }}</div>
        </div>
    </div>
</body>
</html>
'''

# ========== USER DASHBOARD ==========
USER_DASHBOARD = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم - كافية {{ cafe_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            font-family: 'Cairo', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 40px;
            max-width: 550px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
        }
        .success-icon { font-size: 70px; margin-bottom: 20px; animation: scale 0.5s ease; }
        @keyframes scale { 0% { transform: scale(0); } 100% { transform: scale(1); } }
        h1 { color: #00ff88; font-size: 28px; margin-bottom: 10px; }
        .card-number { background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 15px; margin: 20px 0; font-family: monospace; font-size: 24px; letter-spacing: 2px; color: #ff8c42; }
        .stats { display: flex; gap: 15px; margin: 25px 0; flex-wrap: wrap; }
        .stat-card { background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 15px; flex: 1; text-align: center; }
        .stat-label { color: rgba(255, 255, 255, 0.6); font-size: 12px; }
        .stat-value { color: #fff; font-size: 28px; font-weight: bold; }
        .progress-bar { background: rgba(255, 255, 255, 0.1); border-radius: 15px; height: 20px; margin: 20px 0; overflow: hidden; }
        .progress-fill { background: linear-gradient(90deg, #ff6b35, #ff8c42); width: 0%; height: 100%; border-radius: 15px; transition: width 0.5s ease; }
        .timer { font-size: 48px; font-family: monospace; color: #00ff88; margin: 20px 0; font-weight: bold; }
        .buttons { display: flex; gap: 15px; margin-top: 25px; }
        .btn-primary { flex: 1; padding: 15px; background: linear-gradient(90deg, #ff6b35, #ff8c42); border: none; border-radius: 15px; color: #fff; font-size: 16px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; }
        .btn-danger { flex: 1; padding: 15px; background: rgba(255, 51, 51, 0.8); border: none; border-radius: 15px; color: #fff; font-size: 16px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; }
        .warning { color: #ffaa44; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>مرحباً بك في كافية {{ cafe_name }}</h1>
        <div class="card-number">📱 الكرت: {{ card_number }}</div>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">الرصيد المتبقي</div>
                <div class="stat-value">{{ remaining_data }} MB</div>
                <div class="data-info">{{ remaining_percent }}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">الوقت المتبقي</div>
                <div class="timer" id="timer">--:--:--</div>
            </div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ remaining_percent }}%"></div>
        </div>
        <div class="buttons">
            <a href="https://www.google.com" class="btn-primary">🌐 بدء التصفح</a>
            <a href="/logout" class="btn-danger">🚪 إنهاء الجلسة</a>
        </div>
        <div class="warning">⚠️ سيتم قطع الإنترنت تلقائياً عند انتهاء الرصيد</div>
    </div>
    <script>
        let remainingSeconds = {{ remaining_seconds }};
        const timerElement = document.getElementById('timer');
        function formatTime(seconds) {
            let hours = Math.floor(seconds / 3600);
            let minutes = Math.floor((seconds % 3600) / 60);
            let secs = seconds % 60;
            return String(hours).padStart(2,'0') + ':' + String(minutes).padStart(2,'0') + ':' + String(secs).padStart(2,'0');
        }
        function updateTimer() {
            timerElement.innerHTML = formatTime(remainingSeconds);
            if(remainingSeconds <= 0) {
                timerElement.innerHTML = '00:00:00';
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
    <title>دخول الأدمن</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);font-family:'Cairo',sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center}
        .login-box{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:30px;padding:40px;width:400px;border:1px solid rgba(255,255,255,0.2);text-align:center}
        .login-box h1{color:#ff6b35;margin-bottom:30px}
        .login-box input{width:100%;padding:15px;margin:10px 0;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);border-radius:15px;color:#fff;font-size:16px}
        .login-box input:focus{outline:none;border-color:#ff6b35}
        .login-box button{width:100%;padding:15px;background:linear-gradient(90deg,#ff6b35,#ff8c42);border:none;border-radius:15px;color:#fff;font-size:18px;font-weight:bold;cursor:pointer;margin-top:15px}
        .error{color:#ff6b6b;margin-top:15px}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 دخول الأدمن</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
        <div class="error">{{ error }}</div>
    </div>
</body>
</html>
'''

# ========== ADMIN PANEL HTML ==========
ADMIN_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم - كافية الواحة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0a0a;font-family:'Cairo',sans-serif;padding:20px}
        .container{max-width:1400px;margin:auto}
        h1{color:#ff6b35;text-align:center;margin-bottom:30px;font-size:32px}
        .stats{display:flex;gap:20px;margin-bottom:30px;flex-wrap:wrap}
        .stat-card{background:linear-gradient(135deg,#1a1a1a,#2a2a2a);border-radius:20px;padding:25px;flex:1;text-align:center;border:1px solid #ff6b35}
        .stat-number{font-size:48px;color:#00ff88;font-weight:bold}
        .stat-label{color:#888;margin-top:10px}
        .menu{display:flex;gap:15px;margin-bottom:30px;flex-wrap:wrap;justify-content:center}
        .btn{background:linear-gradient(90deg,#ff6b35,#ff8c42);color:#fff;padding:12px 25px;text-decoration:none;border-radius:15px;font-weight:bold}
        .btn-danger{background:#ff0033}
        .card{background:#1a1a1a;border-radius:20px;padding:25px;margin-bottom:30px;border:1px solid #ff6b35}
        .card h2{color:#ff8c42;margin-bottom:20px}
        table{width:100%;border-collapse:collapse}
        th,td{padding:12px;text-align:center;border-bottom:1px solid #333}
        th{color:#ff6b35}
        td{color:#fff}
        input,select{padding:12px;margin:5px;background:#0a0a0a;border:1px solid #ff6b35;border-radius:10px;color:#fff}
        button{padding:12px 25px;background:linear-gradient(90deg,#ff6b35,#ff8c42);border:none;border-radius:10px;color:#fff;cursor:pointer}
        .available{color:#00ff88}
        .used{color:#ff0033}
        .success{color:#00ff88}
        .error{color:#ff0033}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 لوحة تحكم الأدمن - كافية الواحة</h1>
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{{ active_sessions }}</div><div class="stat-label">متصلون الآن</div></div>
            <div class="stat-card"><div class="stat-number">{{ total_cards }}</div><div class="stat-label">إجمالي الكروت</div></div>
            <div class="stat-card"><div class="stat-number">{{ used_cards }}</div><div class="stat-label">كروت مستخدمة</div></div>
            <div class="stat-card"><div class="stat-number">{{ available_cards }}</div><div class="stat-label">كروت متاحة</div></div>
        </div>
        <div class="menu">
            <a href="/admin" class="btn">📊 الرئيسية</a>
            <a href="/admin/cards" class="btn">💳 الكروت</a>
            <a href="/admin/sessions" class="btn">🟢 الجلسات</a>
            <a href="/admin/bulk-cards" class="btn">📦 إنشاء كروت جماعية</a>
            <a href="/admin/logout" class="btn btn-danger">🚪 خروج</a>
        </div>
        <div class="card">
            <h2>➕ إضافة كرت جديد</h2>
            <form method="POST" action="/admin/add">
                <input type="text" name="card_number" placeholder="رقم الكرت" required>
                <select name="data_mb">
                    <option value="500">500 ميجابايت (10 جنيه)</option>
                    <option value="1024">1 جيجابايت (15 جنيه)</option>
                    <option value="2048">2 جيجابايت (25 جنيه)</option>
                    <option value="4096">4 جيجابايت (40 جنيه)</option>
                </select>
                <button type="submit">➕ إضافة</button>
            </form>
        </div>
        <div class="card">
            <h2>📦 إنشاء كروت جماعية</h2>
            <form method="POST" action="/admin/bulk-cards">
                <input type="number" name="quantity" placeholder="الكمية" min="1" max="100" required style="width:150px">
                <select name="data_mb">
                    <option value="500">500 ميجابايت (10 جنيه)</option>
                    <option value="1024">1 جيجابايت (15 جنيه)</option>
                    <option value="2048">2 جيجابايت (25 جنيه)</option>
                    <option value="4096">4 جيجابايت (40 جنيه)</option>
                </select>
                <button type="submit">📦 إنشاء {{ quantity }} كرت</button>
            </form>
        </div>
        <div class="card">
            <h2>📊 آخر الكروت المضافة</h2>
            <div style="overflow-x:auto">
                <table>
                    <thead><tr><th>ID</th><th>رقم الكرت</th><th>الرصيد (MB)</th><th>تاريخ الإضافة</th><th>الحالة</th></tr></thead>
                    <tbody>{{ cards_table }}</tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
'''

# ========== DATABASE FUNCTIONS ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  card_number TEXT UNIQUE,
                  data_mb INTEGER DEFAULT 0,
                  created_at TEXT,
                  used INTEGER DEFAULT 0,
                  used_by TEXT,
                  used_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  card_number TEXT,
                  ip TEXT,
                  start_time TEXT,
                  data_mb INTEGER DEFAULT 0,
                  remaining_data INTEGER DEFAULT 0,
                  status TEXT DEFAULT 'active')''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS failed_logins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip TEXT,
                  attempt_time TEXT,
                  blocked_until TEXT)''')
    
    # كروت تجريبية
    demo_cards = [
        ('123456', 500),
        ('111111', 1024),
        ('222222', 2048),
        ('333333', 4096),
    ]
    
    now = datetime.datetime.now().isoformat()
    for card, data_mb in demo_cards:
        c.execute("INSERT OR IGNORE INTO cards (card_number, data_mb, created_at) VALUES (?, ?, ?)",
                  (card, data_mb, now))
    
    conn.commit()
    conn.close()
    print("[✅] Database initialized")

def check_card(card_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT card_number, data_mb FROM cards WHERE card_number=? AND used=0", (card_number,))
    card = c.fetchone()
    conn.close()
    return card

def use_card(card_number, ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE cards SET used=1, used_by=?, used_at=? WHERE card_number=?", 
              (ip, datetime.datetime.now().isoformat(), card_number))
    conn.commit()
    conn.close()

def add_session(card_number, ip, data_mb):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (card_number, ip, start_time, data_mb, remaining_data, status) VALUES (?, ?, ?, ?, ?, 'active')",
              (card_number, ip, datetime.datetime.now().isoformat(), data_mb, data_mb))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_all_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, card_number, data_mb, created_at, used FROM cards ORDER BY id DESC LIMIT 20")
    cards = c.fetchall()
    conn.close()
    return cards

def get_all_active_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, card_number, ip, start_time, data_mb, remaining_data FROM sessions WHERE status='active' ORDER BY id DESC")
    sessions = c.fetchall()
    conn.close()
    return sessions

def add_card(card_number, data_mb):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO cards (card_number, data_mb, created_at) VALUES (?, ?, ?)",
                  (card_number, data_mb, datetime.datetime.now().isoformat()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def generate_cards_bulk(quantity, data_mb):
    """إنشاء كمية كبيرة من الكروت عشوائية"""
    created = 0
    cards_list = []
    
    for i in range(quantity):
        # توليد رقم كرت عشوائي مكون من 8-12 رقم
        card_length = random.randint(8, 12)
        card_number = ''.join(random.choices(string.digits, k=card_length))
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO cards (card_number, data_mb, created_at) VALUES (?, ?, ?)",
                      (card_number, data_mb, datetime.datetime.now().isoformat()))
            conn.commit()
            created += 1
            cards_list.append(card_number)
        except:
            pass
        finally:
            conn.close()
    
    return created, cards_list

def get_used_cards_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE used=1")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_available_cards_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE used=0")
    count = c.fetchone()[0]
    conn.close()
    return count

def end_session(ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET status='ended' WHERE ip=? AND status='active'", (ip,))
    conn.commit()
    conn.close()

# ========== PROTECTION FUNCTIONS ==========
def is_ip_blocked(ip):
    """التحقق إذا كان الـ IP محظوراً"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT blocked_until FROM failed_logins WHERE ip=? ORDER BY id DESC LIMIT 1", (ip,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        blocked_until = datetime.datetime.fromisoformat(result[0])
        if datetime.datetime.now() < blocked_until:
            return True, blocked_until
    return False, None

def record_failed_attempt(ip):
    """تسجيل محاولة فاشلة"""
    now = datetime.datetime.now()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # حذف المحاولات القديمة (أكثر من ساعة)
    c.execute("DELETE FROM failed_logins WHERE attempt_time < ?", 
              ((now - datetime.timedelta(hours=1)).isoformat(),))
    
    # تسجيل المحاولة الجديدة
    c.execute("INSERT INTO failed_logins (ip, attempt_time) VALUES (?, ?)",
              (ip, now.isoformat()))
    
    # حساب عدد المحاولات في آخر 10 دقائق
    c.execute("SELECT COUNT(*) FROM failed_logins WHERE ip=? AND attempt_time > ?",
              (ip, (now - datetime.timedelta(minutes=10)).isoformat()))
    count = c.fetchone()[0]
    
    # إذا تجاوز الحد، حظر الـ IP
    if count >= MAX_FAILED_ATTEMPTS:
        blocked_until = now + datetime.timedelta(minutes=BLOCK_TIME_MINUTES)
        c.execute("UPDATE failed_logins SET blocked_until=? WHERE ip=? AND blocked_until IS NULL",
                  (blocked_until.isoformat(), ip))
        conn.commit()
        conn.close()
        return True, blocked_until
    
    conn.commit()
    conn.close()
    return False, None

def clear_failed_attempts(ip):
    """مسح محاولات الفشل بعد نجاح الدخول"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM failed_logins WHERE ip=?", (ip,))
    conn.commit()
    conn.close()

# ========== ACTIVE SESSIONS ==========
active_sessions = {}

# ========== GET LOCAL IP ==========
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    client_ip = request.remote_addr
    print(f"[🌐] Client {client_ip} connected")
    
    # التحقق من الحظر
    blocked, blocked_until = is_ip_blocked(client_ip)
    if blocked:
        remaining = (blocked_until - datetime.datetime.now()).seconds // 60
        return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER, 
                                      error="", warning=f"⚠️ تم حظرك بسبب كثرة المحاولات الخاطئة. حاول مرة أخرى بعد {remaining} دقيقة")
    
    return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER, error="", warning="")

@app.route('/login', methods=['POST'])
def login():
    card_number = request.form.get('username')
    client_ip = request.remote_addr
    
    # التحقق من الحظر
    blocked, blocked_until = is_ip_blocked(client_ip)
    if blocked:
        remaining = (blocked_until - datetime.datetime.now()).seconds // 60
        return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER, 
                                      error="", warning=f"⚠️ تم حظرك بسبب كثرة المحاولات الخاطئة. حاول مرة أخرى بعد {remaining} دقيقة")
    
    card = check_card(card_number)
    
    if card:
        # نجاح الدخول - مسح المحاولات الفاشلة
        clear_failed_attempts(client_ip)
        
        data_mb = card[1]
        use_card(card_number, client_ip)
        session_id = add_session(card_number, client_ip, data_mb)
        
        start_time = datetime.datetime.now()
        # حساب الوقت التقريبي (1 ساعة لكل 500 ميجابايت تقريباً)
        hours = max(1, data_mb // 500)
        if data_mb % 500 > 0:
            hours += 1
        end_time = start_time + datetime.timedelta(hours=hours)
        total_seconds = hours * 3600
        
        active_sessions[client_ip] = {
            'card_number': card_number,
            'start_time': start_time,
            'end_time': end_time,
            'data_mb': data_mb,
            'remaining_data': data_mb,
            'remaining_seconds': total_seconds,
            'session_id': session_id
        }
        
        print(f"[✅] Card {card_number} activated from {client_ip} ({data_mb} MB)")
        remaining_percent = 100
        
        return render_template_string(USER_DASHBOARD,
                                      cafe_name=CAFE_NAME,
                                      card_number=card_number,
                                      ip=client_ip,
                                      start_time=start_time.strftime("%H:%M:%S"),
                                      end_time=end_time.strftime("%H:%M:%S"),
                                      remaining_data=data_mb,
                                      remaining_percent=remaining_percent,
                                      remaining_seconds=total_seconds)
    else:
        # تسجيل محاولة فاشلة
        blocked, blocked_until = record_failed_attempt(client_ip)
        remaining_attempts = MAX_FAILED_ATTEMPTS - get_failed_attempts_count(client_ip)
        
        print(f"[❌] Invalid card {card_number} from {client_ip} (Attempts left: {remaining_attempts})")
        
        if blocked:
            remaining = (blocked_until - datetime.datetime.now()).seconds // 60
            return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER,
                                          error="", warning=f"⚠️ تم حظرك بسبب كثرة المحاولات الخاطئة. حاول مرة أخرى بعد {remaining} دقيقة")
        
        return render_template_string(CAPTIVE_PAGE, cafe_name=CAFE_NAME, service_number=SERVICE_NUMBER,
                                      error=f"❌ رقم الكرت غير صالح أو مستخدم (تبقى {remaining_attempts} محاولات)", warning="")

def get_failed_attempts_count(ip):
    """الحصول على عدد المحاولات الفاشلة في آخر 10 دقائق"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ten_min_ago = (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    c.execute("SELECT COUNT(*) FROM failed_logins WHERE ip=? AND attempt_time > ?", (ip, ten_min_ago))
    count = c.fetchone()[0]
    conn.close()
    return count

@app.route('/logout')
def logout():
    client_ip = request.remote_addr
    if client_ip in active_sessions:
        end_session(client_ip)
        del active_sessions[client_ip]
    return redirect('/')

@app.route('/generate_204')
def generate_204():
    return redirect('/')

@app.route('/hotspot-detect.html')
def hotspot_detect():
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
    
    return render_template_string(ADMIN_LOGIN_PAGE, error=error)

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
    available = get_available_cards_count()
    
    cards_html = ""
    for card in cards[:10]:
        status = "❌ مستخدم" if card[4] else "✅ متاح"
        status_class = "used" if card[4] else "available"
        cards_html += f"<tr><td>{card[0]}</td><td>{card[1]}</td><td>{card[2]}</td><td>{card[3][:10]}</td><td class='{status_class}'>{status}</td></tr>"
    
    return render_template_string(ADMIN_PANEL_HTML,
                                  active_sessions=active,
                                  total_cards=len(cards),
                                  used_cards=used,
                                  available_cards=available,
                                  cards_table=cards_html,
                                  quantity=10)

@app.route('/admin/cards')
def admin_cards():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    cards = get_all_cards()
    available = get_available_cards_count()
    used = get_used_cards_count()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>الكروت - كافية الواحة</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#0a0a0a;font-family:'Cairo',sans-serif;padding:20px}}
            .container{{max-width:1200px;margin:auto}}
            h1{{color:#ff6b35;text-align:center;margin-bottom:30px}}
            .stats{{display:flex;gap:20px;margin-bottom:30px}}
            .stat{{background:#1a1a1a;border:1px solid #ff6b35;border-radius:15px;padding:20px;flex:1;text-align:center}}
            .stat-number{{font-size:36px;color:#00ff88;font-weight:bold}}
            table{{width:100%;border-collapse:collapse;margin-top:20px}}
            th,td{{padding:12px;text-align:center;border-bottom:1px solid #333}}
            th{{color:#ff6b35}}
            td{{color:#fff}}
            .available{{color:#00ff88}}
            .used{{color:#ff0033}}
            .back{{color:#ff6b35;text-decoration:none;display:inline-block;margin-bottom:20px}}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/admin" class="back">← رجوع للوحة الرئيسية</a>
            <h1>💳 إدارة الكروت</h1>
            <div class="stats">
                <div class="stat"><div class="stat-number">{len(cards)}</div><div>إجمالي الكروت</div></div>
                <div class="stat"><div class="stat-number">{available}</div><div>✅ كروت متاحة</div></div>
                <div class="stat"><div class="stat-number">{used}</div><div>❌ كروت مستخدمة</div></div>
            </div>
            <div style="overflow-x:auto">
                <table>
                    <thead><tr><th>ID</th><th>رقم الكرت</th><th>الرصيد (MB)</th><th>تاريخ الإضافة</th><th>الحالة</th></tr></thead>
                    <tbody>
    '''
    
    for card in cards:
        status = "❌ مستخدم" if card[4] else "✅ متاح"
        status_class = "used" if card[4] else "available"
        html += f"<tr><td>{card[0]}</td><td>{card[1]}</td><td>{card[2]}</td><td>{card[3][:10]}</td><td class='{status_class}'>{status}</td></tr>"
    
    html += '''
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/admin/sessions')
def admin_sessions():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    sessions = get_all_active_sessions()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>الجلسات النشطة - كافية الواحة</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#0a0a0a;font-family:'Cairo',sans-serif;padding:20px}}
            .container{{max-width:1200px;margin:auto}}
            h1{{color:#ff6b35;text-align:center;margin-bottom:30px}}
            .stats{{background:#1a1a1a;border:1px solid #ff6b35;border-radius:15px;padding:20px;margin-bottom:30px;text-align:center}}
            .stats .number{{font-size:36px;color:#00ff88;font-weight:bold}}
            table{{width:100%;border-collapse:collapse}}
            th,td{{padding:12px;text-align:center;border-bottom:1px solid #333}}
            th{{color:#ff6b35}}
            td{{color:#fff}}
            .active{{color:#00ff88}}
            .back{{color:#ff6b35;text-decoration:none;display:inline-block;margin-bottom:20px}}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/admin" class="back">← رجوع للوحة الرئيسية</a>
            <h1>🟢 الجلسات النشطة</h1>
            <div class="stats"><div class="number">{len(sessions)}</div><div>جلسة نشطة حالياً</div></div>
            <div style="overflow-x:auto">
                <table>
                    <thead><tr><th>ID</th><th>رقم الكرت</th><th>IP</th><th>وقت البدء</th><th>الرصيد (MB)</th><th>المتبقي</th><th>الحالة</th></tr></thead>
                    <tbody>
    '''
    
    for sess in sessions:
        remaining_percent = int((sess[5] / sess[4]) * 100) if sess[4] > 0 else 0
        html += f"<tr><td>{sess[0]}</td><td>{sess[1]}</td><td>{sess[2]}</td><td>{sess[3][:16]}</td><td>{sess[4]}</td><td>{sess[5]} MB ({remaining_percent}%)</td><td class='active'>🟢 نشط</td></tr>"
    
    html += '''
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    card_number = request.form.get('card_number')
    data_mb = int(request.form.get('data_mb', 500))
    
    if add_card(card_number, data_mb):
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><meta http-equiv="refresh" content="2;url=/admin">
        <style>body{{background:#0a0a0a;color:#00ff88;text-align:center;padding:50px}}</style>
        </head>
        <body><h1>✅ تم إضافة الكرت {card_number}</h1><p>الرصيد: {data_mb} ميجابايت</p><p>جاري التحويل...</p></body></html>
        '''
    else:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><meta http-equiv="refresh" content="2;url=/admin">
        <style>body{{background:#0a0a0a;color:#ff0033;text-align:center;padding:50px}}</style>
        </head>
        <body><h1>❌ الكرت {card_number} موجود</h1><p>جاري التحويل...</p></body></html>
        '''

@app.route('/admin/bulk-cards', methods=['GET', 'POST'])
def admin_bulk_cards():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
        data_mb = int(request.form.get('data_mb', 500))
        
        if quantity > 100:
            quantity = 100
        
        created, cards_list = generate_cards_bulk(quantity, data_mb)
        
        cards_text = "<br>".join(cards_list[:20])
        if len(cards_list) > 20:
            cards_text += f"<br>... و{len(cards_list) - 20} كروت أخرى"
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><meta http-equiv="refresh" content="5;url=/admin">
        <style>
            body{{background:#0a0a0a;font-family:sans-serif;text-align:center;padding:50px}}
            .success{{color:#00ff88}}
            .info{{color:#ff8c42;margin:20px 0}}
        </style>
        </head>
        <body>
            <h1 class="success">✅ تم إنشاء {created} كرت</h1>
            <div class="info">الرصيد: {data_mb} ميجابايت لكل كرت</div>
            <div style="background:#1a1a1a;padding:20px;border-radius:10px;max-width:600px;margin:auto">
                <strong>الكروت:</strong><br>{cards_text}
            </div>
            <p>جاري التحويل إلى لوحة التحكم...</p>
        </body>
        </html>
        '''
    
    return redirect('/admin')

# ========== MAIN ==========
def main():
    SERVER_IP = get_local_ip()
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    ☕ نظام كافية الواحة ☕                        ║
║                                                                   ║
║   • تفعيل بالبيانات (ميجابايت)                                   ║
║   • حماية من التخمين (5 محاولات ثم حظر 10 دقائق)                 ║
║   • إنشاء كروت جماعية (كمية مرة واحدة)                          ║
║   • صفحة مستخدم جذابة                                            ║
║   • لوحة تحكم أدمن متكاملة                                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    init_db()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                          ✅ SYSTEM READY                          ║
╠═══════════════════════════════════════════════════════════════════╣
║   🌐 صفحة تسجيل الدخول: http://{SERVER_IP}:{PORT}                 ║
║   🔧 لوحة الأدمن: http://{SERVER_IP}:{PORT}/admin                 ║
║                                                                   ║
║   🔐 بيانات دخول الأدمن: admin / admin123                         ║
║   📝 كروت تجريبية:                                                ║
║       123456 → 500 ميجابايت                                      ║
║       111111 → 1 جيجابايت                                        ║
║       222222 → 2 جيجابايت                                        ║
║       333333 → 4 جيجابايت                                        ║
║                                                                   ║
║   🛡️ نظام الحماية: {MAX_FAILED_ATTEMPTS} محاولات ثم حظر {BLOCK_TIME_MINUTES} دقيقة   ║
║   📦 إنشاء كروت جماعية: متاح في لوحة الأدمن                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    main()