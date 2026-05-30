#!/usr/bin/env python3
"""
☕ نظام كافية الواحة - نسخة السحابة ☕
"""

import os
import sys
import sqlite3
import datetime
import socket
import hashlib
from flask import Flask, request, redirect, jsonify, session

# ========== CONFIGURATION ==========
PORT = int(os.environ.get("PORT", 8080))
CAFE_NAME = "الواحة"
SERVICE_NUMBER = "01273834877"

# ========== ADMIN PROTECTION ==========
ADMIN_USERNAME = "admin01208571***Fm"
ADMIN_PASSWORD = "01208571***FmPass"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)

# ========== FLASK APP ==========
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== HTML PAGES (كدوال) ==========
CAPTIVE_PAGE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>☕ كافية الواحة</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);font-family:'Cairo','Tahoma',sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center}
        .container{background:rgba(0,0,0,0.85);border-radius:20px;padding:40px;max-width:450px;width:90%;border:2px solid #ff6b35;box-shadow:0 0 30px rgba(255,107,53,0.3);text-align:center}
        h1{color:#ff6b35;margin-bottom:10px;font-size:28px}
        .logo{font-size:60px;margin-bottom:10px}
        input{width:100%;padding:15px;margin:10px 0;background:#1a1a1a;border:1px solid #ff6b35;border-radius:10px;color:#ff6b35;font-size:18px;text-align:center}
        button{width:100%;padding:15px;background:linear-gradient(90deg,#ff6b35,#ff8c42);border:none;border-radius:10px;color:#fff;font-size:20px;font-weight:bold;cursor:pointer;margin-top:10px}
        .error{color:#ff0033;margin-top:10px}
        .footer{color:#555;font-size:12px;margin-top:20px}
        .contact{color:#ff6b35;margin-top:15px}
        .prices{display:flex;gap:10px;margin-top:20px}
        .price-card{background:#1a1a1a;padding:10px;border-radius:10px;flex:1}
        .price-card .hours{color:#ff6b35;font-size:20px;font-weight:bold}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">☕</div>
        <h1>كافية الواحة</h1>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="📱 رقم الكرت" required autofocus>
            <button type="submit">🚀 دخول الإنترنت</button>
        </form>
        <div class="error">{{ error }}</div>
        <div class="prices">
            <div class="price-card"><div class="hours">1 ساعة</div><div>10 ج</div></div>
            <div class="price-card"><div class="hours">2 ساعة</div><div>15 ج</div></div>
            <div class="price-card"><div class="hours">4 ساعة</div><div>25 ج</div></div>
            <div class="price-card"><div class="hours">8 ساعة</div><div>40 ج</div></div>
        </div>
        <div class="footer"><div class="contact">📞 للكروت: 01273834877</div></div>
    </div>
</body>
</html>
'''

def get_captive_page(error=""):
    return CAPTIVE_PAGE.replace("{{ error }}", error)

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
    
    demo_cards = [('123456', 60), ('111111', 120), ('222222', 240), ('333333', 480)]
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
    return get_captive_page()

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
        
        active_sessions[client_ip] = {
            'card_number': card_number,
            'start_time': start_time,
            'minutes': minutes
        }
        
        print(f"[✅] Card {card_number} activated from {client_ip} ({minutes} minutes)")
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="2;url=https://www.google.com">
            <title>تم التسجيل</title>
            <style>
                body{{background:#0a0a0a;color:#00ff41;font-family:monospace;text-align:center;padding:50px}}
                .timer{{font-size:48px;margin:20px}}
            </style>
        </head>
        <body>
            <h1>✅ مرحباً {card_number}</h1>
            <p>الوقت المتبقي: {minutes} دقيقة</p>
            <div class="timer" id="timer"></div>
            <p>جاري تحويلك إلى الإنترنت...</p>
            <script>
                let remaining = {minutes * 60};
                const timer = document.getElementById('timer');
                function update() {{
                    let m = Math.floor(remaining / 60);
                    let s = remaining % 60;
                    timer.innerHTML = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                    if(remaining > 0) {{ remaining--; setTimeout(update, 1000); }}
                }}
                update();
            </script>
        </body>
        </html>
        '''
    else:
        print(f"[❌] Invalid card {card_number} from {client_ip}")
        return get_captive_page(error="❌ رقم الكرت غير صالح أو مستخدم")

@app.route('/logout')
def logout():
    client_ip = request.remote_addr
    if client_ip in active_sessions:
        del active_sessions[client_ip]
    return redirect('/')

# مسارات Captive Portal
@app.route('/generate_204')
def generate_204():
    return redirect('/')

@app.route('/hotspot-detect.html')
def hotspot_detect():
    return redirect('/')

# ========== ADMIN ROUTES (مبسطة) ==========
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            return '''
            <!DOCTYPE html>
            <html><head><meta charset="UTF-8"></head>
            <body style="background:#0a0a0a;color:#ff0033;text-align:center;padding:50px">
                <h1>❌ خطأ في الدخول</h1>
                <a href="/admin/login" style="color:#00ff41">حاول مرة أخرى</a>
            </body>
            </html>
            '''
    
    return '''
    <!DOCTYPE html>
    <html lang="ar">
    <head><meta charset="UTF-8"><title>دخول الأدمن</title>
    <style>
        body{background:#0a0a0a;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh}
        .box{background:#1a1a1a;padding:40px;border-radius:10px;border:2px solid #ff0033;text-align:center}
        input{width:100%;padding:10px;margin:10px 0;background:#0a0a0a;border:1px solid #ff0033;color:#00ff41;border-radius:5px}
        button{padding:10px 20px;background:#ff0033;color:#fff;border:none;border-radius:5px;cursor:pointer}
    </style>
    </head>
    <body>
    <div class="box">
        <h1 style="color:#ff0033">🔐 دخول الأدمن</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
    </div>
    </body>
    </html>
    '''

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
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>لوحة الأدمن</title>
    <style>
        body{{background:#0a0a0a;font-family:sans-serif;padding:20px}}
        h1{{color:#ff6b35;text-align:center}}
        .stats{{display:flex;gap:15px;margin-bottom:20px}}
        .stat{{background:#1a1a1a;border:1px solid #ff6b35;border-radius:10px;padding:15px;text-align:center;flex:1}}
        .stat-number{{font-size:36px;color:#00ff41}}
        .menu{{display:flex;gap:10px;justify-content:center;margin-bottom:20px}}
        .btn{{background:#ff6b35;color:#fff;padding:10px 20px;text-decoration:none;border-radius:8px}}
        .card{{background:#1a1a1a;border:1px solid #ff6b35;border-radius:10px;padding:20px;margin-bottom:20px}}
        table{{width:100%;border-collapse:collapse}}
        th,td{{padding:10px;border-bottom:1px solid #333}}
        th{{color:#ff6b35}}
        td{{color:#fff}}
        input,select{{padding:8px;margin:5px;background:#0a0a0a;border:1px solid #ff6b35;color:#fff;border-radius:5px}}
        button{{padding:8px 15px;background:#ff6b35;color:#fff;border:none;border-radius:5px;cursor:pointer}}
    </style>
    </head>
    <body>
        <h1>🔧 لوحة تحكم الأدمن</h1>
        <div class="stats">
            <div class="stat"><div class="stat-number">{active}</div><div>متصلون الآن</div></div>
            <div class="stat"><div class="stat-number">{len(cards)}</div><div>إجمالي الكروت</div></div>
            <div class="stat"><div class="stat-number">{used}</div><div>كروت مستخدمة</div></div>
        </div>
        <div class="menu">
            <a href="/admin" class="btn">📊 الرئيسية</a>
            <a href="/admin/cards" class="btn">💳 الكروت</a>
            <a href="/admin/logout" class="btn">🚪 خروج</a>
        </div>
        <div class="card">
            <h2>➕ إضافة كرت جديد</h2>
            <form method="POST" action="/admin/add">
                <input type="text" name="username" placeholder="رقم الكرت" required>
                <select name="minutes">
                    <option value="60">1 ساعة</option>
                    <option value="120">2 ساعة</option>
                    <option value="240">4 ساعة</option>
                    <option value="480">8 ساعة</option>
                </select>
                <button type="submit">➕ إضافة</button>
            </form>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/admin/cards')
def admin_cards():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    cards = get_all_cards()
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>الكروت</title>
    <style>
        body{{background:#0a0a0a;padding:20px}}
        table{{width:100%;border-collapse:collapse}}
        th,td{{padding:10px;border-bottom:1px solid #333}}
        th{{color:#ff6b35}}
        td{{color:#fff}}
        .available{{color:#00ff41}}
        .used{{color:#ff0033}}
        .back{{color:#ff6b35;text-decoration:none;display:inline-block;margin-bottom:20px}}
    </style>
    </head>
    <body>
        <a href="/admin" class="back">← رجوع</a>
        <h1 style="color:#ff6b35">💳 الكروت</h1>
        <p style="color:#888">✅ متاحة: {sum(1 for c in cards if not c[4])} | ❌ مستخدمة: {sum(1 for c in cards if c[4])}</p>
        <table>
            <tr><th>ID</th><th>رقم الكرت</th><th>الدقائق</th><th>تاريخ الإضافة</th><th>الحالة</th></tr>
    '''
    for card in cards:
        status = "❌ مستخدم" if card[4] else "✅ متاح"
        status_class = "used" if card[4] else "available"
        html += f"<tr><td>{card[0]}</td><td>{card[1]}</td><td>{card[2]}</td><td>{card[3][:10]}</td><td class='{status_class}'>{status}</td></tr>"
    html += '</table></body></html>'
    return html

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    card_number = request.form.get('username')
    minutes = int(request.form.get('minutes', 60))
    
    if add_card(card_number, minutes):
        return f'<html><body style="background:#0a0a0a;color:#00ff41;text-align:center;padding:50px"><h1>✅ تم إضافة الكرت {card_number}</h1><a href="/admin" style="color:#ff6b35">العودة</a></body></html>'
    else:
        return f'<html><body style="background:#0a0a0a;color:#ff0033;text-align:center;padding:50px"><h1>❌ الكرت {card_number} موجود</h1><a href="/admin" style="color:#ff6b35">العودة</a></body></html>'

# ========== MAIN ==========
def main():
    SERVER_IP = get_local_ip()
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    ☕ نظام كافية الواحة ☕                        ║
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
║   🔐 بيانات دخول الأدمن: admin01208571***Fm / 01208571***FmPass  ║
║   📝 كروت تجريبية: 123456, 111111, 222222, 333333               ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # تشغيل السيرفر
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    main()