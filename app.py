import base64
import json
import os
import requests
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

KLASSEN_LISTE = [
    "Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", 
    "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", 
    "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", 
    "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard"
]

# --- GITHUB CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "gamer24333"
REPO_NAME = "free_games"
FILE_PATH = "portal_daten.json"  # Wir speichern alles in EINER Datei (Chat + Highscores)

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"} if GITHUB_TOKEN else {}

def load_all_data():
    if not GITHUB_TOKEN:
        return {"chats": {"global": [{"name": "System", "text": "Token fehlt!"}]}, "scores": {}}, None
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return json.loads(content), file_data['sha']
        else:
            # Standard-Struktur, falls Datei noch nicht existiert
            default_data = {
                "chats": {"global": [{"name": "System", "text": "Willkommen im Klassen-Chat! 🤫"}]},
                "scores": {}
            }
            return default_data, None
    except Exception:
        return {"chats": {"global": [{"name": "System", "text": "Verbindungsfehler."}]}, "scores": {}}, None

def save_all_data(data, sha):
    json_string = json.dumps(data, ensure_ascii=False, indent=4)
    content_base64 = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    payload = {"message": "Portal Daten aktualisiert", "content": content_base64}
    if sha:
        payload["sha"] = sha
    requests.put(GITHUB_API_URL, headers=headers, json=payload)

# Helper, um für zwei Personen immer denselben Raumnamen zu generieren (z.B. "Ben_Till")
def get_private_room_name(user1, user2):
    return "_".join(sorted([user1, user2]))


# --- ROUTEN ---

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eingabe_name = request.form.get('nutzername', '').strip()
        if eingabe_name in KLASSEN_LISTE:
            session['username'] = eingabe_name
            return redirect(url_for('dashboard'))
        return render_template('login.html', fehler="Du bist nicht auf der Liste!")
    return render_template('login.html')

@app.route('/welcome')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['username'])

# NEU: Chat-Übersicht & Räume
@app.route('/chat')
@app.route('/chat/<room>')
def chat(room="global"):
    if 'username' not in session: return redirect(url_for('login'))
    
    data, _ = load_all_data()
    current_user = session['username']
    
    # Filter für die Liste der Mitschüler (ohne sich selbst)
    chpartner = [schueler for schueler in KLASSEN_LISTE if schueler != current_user]
    
    # Raumnamen ermitteln, falls es ein privater Chat ist
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    raum_nachrichten = data["chats"].get(actual_room, [])
    
    return render_template('chat.html', room=room, nachrichten=raum_nachrichten, partner=chpartner)

@app.route('/chat/<room>/send', methods=['POST'])
def send_message(room):
    if 'username' not in session: return {"error": "Logn erforderlich"}, 401
    
    nachricht_text = request.form.get('message', '').strip()
    if not nachricht_text: return redirect(url_for('chat', room=room))
    
    data, sha = load_all_data()
    current_user = session['username']
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    if actual_room not in data["chats"]:
        data["chats"][actual_room] = []
        
    data["chats"][actual_room].append({"name": current_user, "text": nachricht_text})
    save_all_data(data, sha)
    
    return redirect(url_for('chat', room=room))

# API für Live-Updates im Chat
@app.route('/api/chat-messages/<room>')
def get_api_messages(room):
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data, _ = load_all_data()
    actual_room = room if room == "global" else get_private_room_name(session['username'], room)
    return json.dumps(data["chats"].get(actual_room, []), ensure_ascii=False)

# Geometry Dash & Rangliste
@app.route('/geometry-dash')
def game():
    if 'username' not in session: 
        return redirect(url_for('login'))
    
    data, _ = load_all_data()
    scores_data = data.get("scores", {})
    
    # Hier bauen wir die vollständige Liste für ALLE Schüler
    vollstaendige_liste = []
    for schueler in KLASSEN_LISTE:
        # Falls der Schüler schon gespielt hat, nimm seinen Score, sonst 0
        score = scores_data.get(schueler, 0)
        vollstaendige_liste.append((schueler, score))
    
    # Jetzt sortieren wir alle Schüler nach ihrem Score (höchster zuerst)
    leaderboard = sorted(vollstaendige_liste, key=lambda x: x[1], reverse=True)
    
    return render_template('game.html', leaderboard=leaderboard)
    
@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    score = int(request.json.get('score', 0))
    current_user = session['username']
    
    data, sha = load_all_data()
    # Nur speichern, wenn es besser als der alte Highscore ist
    old_score = data["scores"].get(current_user, 0)
    if score > old_score:
        data["scores"][current_user] = score
        save_all_data(data, sha)
    return {"status": "success"}

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/chat/<room>/delete/<int:msg_index>', methods=['POST'])
def delete_message(room, msg_index):
    if 'username' not in session:
        return {"error": "Login erforderlich"}, 401
    
    data, sha = load_all_data()
    current_user = session['username']
    
    # Raumnamen für private Chats ermitteln
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    if actual_room in data["chats"]:
        raum_nachrichten = data["chats"][actual_room]
        
        # Sicherheitcheck: Nur der Absender der Nachricht darf sie löschen!
        if 0 <= msg_index < len(raum_nachrichten):
            if raum_nachrichten[msg_index]["name"] == current_user:
                # Nachricht entfernen
                raum_nachrichten.pop(msg_index)
                save_all_data(data, sha)
                
    return redirect(url_for('chat', room=room))

if __name__ == '__main__':
    app.run(debug=True)
