from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import threading
import time
import random
import uuid
import requests
import json
import os  # ← Render ke liye add kiya

app = Flask(__name__)
app.secret_key = "hawksujal"  # Change kar sakta hai

# ====================== SECURITY SETTINGS ======================
MASTER_PASSWORD = "sujal@007"   # ← YE CHANGE KAR LE APNA
TELEGRAM_TOKEN = "8567970588:AAE4iLtg7v5vGGVprjT3LVadF24Ug63YLZQ"   # ← APNA BOT TOKEN DAAL
OWNER_CHAT_ID = "8383947537"                              # ← APNA TELEGRAM CHAT ID DAAL
# ==============================================================

# For storing pending approvals (code: user_id)
pending_approvals = {}  # dict[code] = user_id
approved_codes = set()

users_data = {}

def send_telegram(text, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": OWNER_CHAT_ID, "text": text, "parse_mode": "HTML"}
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            print(f"Telegram send failed: {response.text}")
    except Exception as e:
        print(f"Telegram send error: {e}")

def add_log(user_id, msg, color="white"):
    if user_id not in users_data:
        users_data[user_id] = {"logs": []}
    timestamp = time.strftime('%H:%M:%S')
    users_data[user_id]["logs"].append({"time": timestamp, "msg": msg, "color": color})
    if len(users_data[user_id]["logs"]) > 500:
        users_data[user_id]["logs"] = users_data[user_id]["logs"][-500:]

def spam_worker(user_id, client, thread_id, messages, delay, cycle_count, cycle_break):
    sent = 0
    while users_data[user_id].get("running", False):
        try:
            msg = random.choice(messages)
            client.direct_send(msg, thread_ids=[thread_id])
            sent += 1
            users_data[user_id]["total_sent"] = users_data[user_id].get("total_sent", 0) + 1
            add_log(user_id, f"Sent #{users_data[user_id]['total_sent']} → {msg[:70]}", "lime")
            if sent % cycle_count == 0:
                add_log(user_id, f"Break {cycle_break}s after {cycle_count} messages", "yellow")
                time.sleep(cycle_break)
            time.sleep(delay * random.uniform(0.9, 1.4))
        except Exception as e:
            add_log(user_id, f"Error: {str(e)}", "red")
            time.sleep(30)

# Updated: Webhook set with Render auto-URL + retries
def set_telegram_webhook():
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not webhook_url:
        webhook_url = "https://instaspam-yixc.onrender.com"  # ← Tera hardcoded URL fallback
    full_url = f"{webhook_url.rstrip('/')}/webhook"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={full_url}"
    
    # Retry 5 times (Render slow hota hai)
    for attempt in range(5):
        try:
            response = requests.get(url, timeout=15)
            result = response.json()
            if result.get('ok'):
                print(f"Webhook set success on attempt {attempt+1}: {full_url}")
                send_telegram(f"🚀 Webhook set! Server ready at {webhook_url}")
                return True
            else:
                print(f"Webhook attempt {attempt+1} failed: {result}")
        except Exception as e:
            print(f"Webhook attempt {attempt+1} error: {e}")
        time.sleep(10)  # 10 sec wait before retry
    
    print("All webhook attempts failed!")
    send_telegram("❌ Webhook set failed! Manual check kar bro")
    return False

# Webhook route to handle Telegram updates (button presses)
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if 'callback_query' in update:
            callback = update['callback_query']
            data = callback.get('data')
            chat_id = callback['from']['id']
            
            # Verify owner and pending code
            if str(chat_id) == OWNER_CHAT_ID and data in pending_approvals:
                approved_codes.add(data)
                send_telegram(f"✅ Access approved for code: <code>{data}</code>")
                # Answer callback to hide loading
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                              data={"callback_query_id": callback['id'], "text": "Approved! Panel unlocked."})
                print(f"Approved code: {data}")
        
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

# Route to check approval status (JS polling use karega)
@app.route('/check_approval')
def check_approval():
    code = request.args.get('code')
    if code and code in approved_codes:
        session['approved'] = True
        approved_codes.remove(code)
        return jsonify({"status": "approved"}), 200
    return jsonify({"status": "pending"}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == MASTER_PASSWORD:
            session['auth'] = True
            return redirect('/')
        else:
            return "<h1>Galat Password Bhai</h1>", 403
    return '''
    <center style="margin-top:15%;font-family:Arial">
    <h1>HAWK SUJAL SPAMMER v9</h1>
    <form method="post">
    <input type="password" name="password" placeholder="Master Password Daal" required 
           style="padding:15px;font-size:18px;width:300px;border-radius:10px;border:none">
    <br><br>
    <button type="submit" style="padding:15px 30px;font-size:18px;background:#ff006e;color:white;border:none;border-radius:10px">
    ENTER PANEL
    </button>
    </form>
    </center>
    '''

@app.route('/', methods=['GET', 'POST'])
def index():
    # Master password check
    if not session.get('auth'):
        return redirect('/login')

    # Telegram approval check
    if not session.get('approved'):
        code = str(random.randint(100000, 999999))
        session['pending_code'] = code
        pending_approvals[code] = session.get('user_id', 'default')
        send_telegram(
            f"<b>🔐 NEW ACCESS REQUEST!</b>\n\n"
            f"Site access try ki hai\n"
            f"Code: <code>{code}</code>\n"
            f"URL: https://instaspam-yixc.onrender.com",
            {"inline_keyboard": [[{"text": "✅ APPROVE ACCESS", "callback_data": code}]]}
        )
        return f'''
        <center style="margin-top:20%;font-family:Arial;color:white;background:#000;height:100vh">
        <h1>WAITING FOR OWNER APPROVAL</h1>
        <h2>Telegram pe request bheji gayi hai</h2>
        <h3>Code: <code>{code}</code></h3>
        <p>Button daba de Telegram pe – 5-10 sec mein approve ho jayega</p>
        <script>
        function checkApproval() {{
            fetch('/check_approval?code={code}')
                .then(res => res.json())
                .then(data => {{
                    if (data.status === 'approved') {{
                        alert('Approved! Redirecting...');
                        location.href = '/';
                    }}
                }})
                .catch(() => {{ console.log('Check failed, retrying...'); }});
        }}
        setInterval(checkApproval, 4000);  // Har 4 sec check
        checkApproval();  // Pehla check immediate
        </script>
        </center>
        '''

    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        users_data[user_id] = {
            "running": False, "total_sent": 0, "status": "Ready",
            "threads": 0, "logs": [], "clients": [], "worker_threads": []
        }

    data = users_data[user_id]

    if request.method == 'POST':
        data["running"] = False
        time.sleep(2)
        data["logs"] = []
        add_log(user_id, "New bombing session started...", "cyan")

        data.update({
            "username": request.form['username'],
            "password": request.form['password'],
            "thread_id": int(request.form['thread_id']),
            "messages": [m.strip() for m in request.form['messages'].split('\n') if m.strip()],
            "delay": float(request.form['delay']),
            "cycle_count": int(request.form['cycle_count']),
            "cycle_break": int(request.form['cycle_break']),
            "threads_num": int(request.form['threads'])
        })

        data["running"] = True
        data["total_sent"] = 0
        data["status"] = "BOMBING ACTIVE"
        data["clients"] = []
        data["worker_threads"] = []

        for i in range(data["threads_num"]):
            cl = Client()
            cl.delay_range = [1, 5]
            try:
                cl.login(data["username"], data["password"])
                add_log(user_id, f"Thread {i+1} → Login Success", "lime")
                data["clients"].append(cl)
                t = threading.Thread(target=spam_worker, args=(user_id, cl,
                    data["thread_id"], data["messages"], data["delay"],
                    data["cycle_count"], data["cycle_break"]), daemon=True)
                t.start()
                data["worker_threads"].append(t)
            except TwoFactorRequired:
                add_log(user_id, "2FA Required! Manual login kar Instagram pe", "orange")
            except Exception as e:
                add_log(user_id, f"Thread {i+1} → Failed: {str(e)}", "red")

        data["threads"] = len(data["clients"])
        if data["clients"]:
            add_log(user_id, "BOMBING STARTED SUCCESSFULLY!", "lime")
        else:
            data["running"] = False
            data["status"] = "Login Failed"

    return render_template('index.html',
        status=data.get("status", "Ready"),
        total_sent=data.get("total_sent", 0),
        threads=data.get("threads", 0),
        logs=data.get("logs", [])
    )

@app.route('/stop')
def stop():
    if not session.get('auth'): return redirect('/login')
    user_id = session.get('user_id')
    if user_id and user_id in users_data:
        users_data[user_id]["running"] = False
        add_log(user_id, "STOP COMMAND → BOMBING STOPPED!", "red")
        users_data[user_id]["status"] = "STOPPED"
    return redirect('/')

@app.route('/clear')
def clear():
    if session.get('auth') and session.get('user_id') in users_data:
        users_data[session['user_id']]["logs"] = []
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    send_telegram("🔄 SPAMMER SERVER STARTING ON RENDER...")
    time.sleep(5)  # Render ko thoda time de
    
    if set_telegram_webhook():
        send_telegram("✅ SERVER FULLY ONLINE! Ready for requests 🚀")
    else:
        send_telegram("⚠️ Server online but webhook issue – manual check kar")
    
    # Render port auto-detect
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
