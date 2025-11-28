# main.py  ← pura replace kar de isse

from flask import Flask, render_template, request, redirect, url_for, session
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import threading
import time
import random
import uuid

app = Flask(__name__)
app.secret_key = "sujal_hawk_king_007_2025_ultimate"

# ← APNA PASSWORD CHANGE KAR LE
MASTER_PASSWORD = "sujal@007"

users_data = {}

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == MASTER_PASSWORD:
            session['auth'] = True
            return redirect('/')
        else:
            return "<h1>Galat Password Bhai</h1>", 403
    return '''
    <center style="margin-top:15%;font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);height:100vh;color:white">
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
    if not session.get('auth'):
        return redirect('/login')

    user_id = session.get('user_id')
    
    # ← YE FIX HAI (agar user_id nahi hai ya server restart ho gaya ho)
    if not user_id or user_id not in users_data:
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
            "delay": float(request.form.get('delay', 8)),
            "cycle_count": int(request.form.get('cycle_count', 50)),
            "cycle_break": int(request.form.get('cycle_break', 35)),
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
                add_log(user_id, "2FA Required! Manual login kar", "orange")
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
        users_data[session.get('user_id')]["logs"] = []
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
