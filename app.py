import base64
import json
import os
import requests
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
# Holt den Secret Key aus den Umgebungsvariablen
app.secret_key = os.environ.get("SECRET_KEY")

# 1. Deine vollständige Klassenliste
KLASSEN_LISTE = [
    "Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", 
    "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", 
    "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", 
    "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard"
]

# --- GITHUB KONFIGURATION ---
# Die geheimen Daten werden jetzt sicher über das System geladen!
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "gamer24333"
REPO_NAME = "free_games"
FILE_PATH = "chat_verlauf.json"

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

# Die Headers werden nur gebaut, wenn ein Token da ist (verhindert Abstürze beim lokalen Starten)
headers = {}
if GITHUB_TOKEN:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def load_messages_from_github():
    if not GITHUB_TOKEN:
        return [{"name": "System", "text": "Fehler: GITHUB_TOKEN wurde nicht auf Render eingerichtet!"}], None
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return json.loads(content), file_data['sha']
        else:
            default_data = [{"name": "System", "text": "Willkommen im permanenten Klassen-Chat! 🤫"}]
            return default_data, None
    except Exception:
        return [{"name": "System", "text": "Verbindungsfehler zu GitHub."}], None

def save_message_to_github(name, text):
    if not GITHUB_TOKEN:
        return
    messages, sha = load_messages_from_github()
    messages.append({"name": name, "text": text})
    
    json_string = json.dumps(messages, ensure_ascii=False, indent=4)
    content_base64 = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": f"Neuer Chat-Beitrag von {name}",
        "content": content_base64
    }
    if sha:
        data["sha"] = sha

    requests.put(GITHUB_API_URL, headers=headers, json=data)


# --- ROUTEN ---

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        eingabe_name = request.form.get('nutzername', '').strip()
        
        if eingabe_name in KLASSEN_LISTE:
            session['username'] = eingabe_name
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', fehler="Du bist leider nicht auf der Gästeliste!")
            
    return render_template('login.html')

@app.route('/welcome')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['username'])

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nachricht_text = request.form.get('message', '').strip()
        if nachricht_text:
            save_message_to_github(session['username'], nachricht_text)
            return redirect(url_for('chat'))

    nachrichten, _ = load_messages_from_github()
    return render_template('chat.html', nachrichten=nachrichten)

@app.route('/api/chat-messages')
def get_api_messages():
    if 'username' not in session:
        return {"error": "Nicht autorisiert"}, 401
    nachrichten, _ = load_messages_from_github()
    return json.dumps(nachrichten, ensure_ascii=False)

@app.route('/geometry-dash')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('game.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
