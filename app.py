import base64
import json
import os
import requests
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
# Standard-Passwort als Fallback, falls kein SECRET_KEY auf Render gesetzt ist
app.secret_key = os.environ.get("SECRET_KEY", "super_geheimes_passwort_fuer_die_klasse")

KLASSEN_LISTE = [
    "Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", 
    "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", "Johann", 
    "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", "Meike",
    "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard"
]

# --- GITHUB CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "gamer24333"
REPO_NAME = "free_games"
FILE_PATH = "portal_daten.json"

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"} if GITHUB_TOKEN else {}

def load_all_data():
    if not GITHUB_TOKEN:
        return {"chats": {"global": []}, "scores": {}, "clicker_scores": {}, "pins": {}, "tictactoe": {}}, None
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            parsed_data = json.loads(content)
            
            # Sicherheitsnetz für alle alten/neuen Datenstrukturen
            if "chats" not in parsed_data: parsed_data["chats"] = {"global": []}
            if "scores" not in parsed_data: parsed_data["scores"] = {}
            if "clicker_scores" not in parsed_data: parsed_data["clicker_scores"] = {}
            if "pins" not in parsed_data: parsed_data["pins"] = {}
            if "tictactoe" not in parsed_data: parsed_data["tictactoe"] = {}
            return parsed_data, file_data['sha']
        else:
            default_data = {
                "chats": {"global": [{"name": "System", "text": "Willkommen im Klassen-Chat! 🤫"}]},
                "scores": {},
                "clicker_scores": {},
                "pins": {},
                "tictactoe": {}
            }
            return default_data, None
    except Exception:
        return {"chats": {"global": []}, "scores": {}, "clicker_scores": {}, "pins": {}, "tictactoe": {}}, None

def save_all_data(data, sha):
    json_string = json.dumps(data, ensure_ascii=False, indent=4)
    content_base64 = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    payload = {"message": "Portal Daten aktualisiert", "content": content_base64}
    if sha:
        payload["sha"] = sha
    requests.put(GITHUB_API_URL, headers=headers, json=payload)

def get_private_room_name(user1, user2):
    return "_".join(sorted([user1, user2]))

def get_ttt_id(p1, p2):
    return f"{min(p1, p2)}_vs_{max(p1, p2)}"


# --- ROUTEN ---

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        eingabe_name = request.form.get('nutzername', '').strip()
        eingabe_pin = request.form.get('pin', '').strip()
        
        if eingabe_name not in KLASSEN_LISTE:
            return render_template('login.html', fehler="Du bist nicht auf der Liste!")
            
        data, sha = load_all_data()
        pins_data = data.get("pins", {})
        
        if eingabe_name in pins_data:
            if pins_data[eingabe_name] == eingabe_pin:
                session['username'] = eingabe_name
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', fehler="Falsche PIN! Jemand versucht wohl dich zu hacken... 🤔", name_vorbefuellt=eingabe_name)
        else:
            if len(eingabe_pin) < 4:
                return render_template('login.html', info="Da dies dein erster Login ist, erstelle bitte eine mindestens 4-stellige PIN!", name_vorbefuellt=eingabe_name)
            
            data["pins"][eingabe_name] = eingabe_pin
            save_all_data(data, sha)
            
            session['username'] = eingabe_name
            return redirect(url_for('dashboard'))
            
    return render_template('login.html')

@app.route('/welcome')
def dashboard():
    if 'username' not in session: 
        return redirect(url_for('login'))
    
    data, _ = load_all_data()
    ttt_games = data.get("tictactoe", {})
    me = session['username']
    
    # 1. Tic-Tac-Toe Einladungen filtern
    aktive_einladungen = []
    for g_id, g_data in ttt_games.items():
        if g_data["gegner"] == me and g_data["status"] == "eingeladen":
            aktive_einladungen.append({"id": g_id, "von": g_data["ersteller"], "is_active": False})
        elif (g_data["ersteller"] == me or g_data["gegner"] == me) and g_data["status"] == "aktiv":
            aktive_einladungen.append({"id": g_id, "von": "Dein Match läuft!", "is_active": True})

    # 2. Prüfen, ob DU der Admin bist (Ersetze "Till" durch deinen exakten Namen aus der Liste)
    is_admin = (me == "Till")

    return render_template('dashboard.html', name=me, einladungen=aktive_einladungen, is_admin=is_admin)

# API für den Dashboard-Zähler: Gibt die Anzahl der globalen Nachrichten zurück
@app.route('/api/dashboard-stats')
def dashboard_stats():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data, _ = load_all_data()
    current_user = session['username']
    
    # Anzahl der globalen Nachrichten
    global_chat_len = len(data["chats"].get("global", []))
    
    # Hier zählen wir die Nachrichten für jeden privaten Chatraum
    private_chats_stats = {}
    for schueler in KLASSEN_LISTE:
        if schueler != current_user:
            room_id = get_private_room_name(current_user, schueler)
            private_chats_stats[schueler] = len(data["chats"].get(room_id, []))
    
    return {
        "global_messages_count": global_chat_len,
        "private_messages_stats": private_chats_stats
    }
# --- 🛠️ DAS ADMIN PANEL ROUTEN ---
@app.route('/admin')
def admin_panel():
    # Ersetze "Till" durch deinen Namen
    if 'username' not in session or session['username'] != "Till":
        return "Zugriff verweigert! ❌", 403
        
    data, _ = load_all_data()
    return render_template('admin.html', pins=data.get("pins", {}))

@app.route('/admin/reset-pin/<schueler>', methods=['POST'])
def admin_reset_pin(schueler):
    if 'username' not in session or session['username'] != "Till": return "403", 403
    
    data, sha = load_all_data()
    if schueler in data["pins"]:
        del data["pins"][schueler] # Löscht die PIN des Schülers -> er kann beim nächsten Login eine neue setzen
        save_all_data(data, sha)
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/clear-chat', methods=['POST'])
def admin_clear_chat():
    if 'username' not in session or session['username'] != "Till": return "403", 403
    
    data, sha = load_all_data()
    data["chats"]["global"] = [{"name": "System", "text": "Der Chat wurde vom Admin aufgeräumt!🧹"}]
    save_all_data(data, sha)
    
    return redirect(url_for('admin_panel'))


# --- CHAT ROUTEN ---

@app.route('/chat')
@app.route('/chat/<room>')
def chat(room="global"):
    if 'username' not in session: return redirect(url_for('login'))
    
    data, _ = load_all_data()
    current_user = session['username']
    chpartner = [schueler for schueler in KLASSEN_LISTE if schueler != current_user]
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    raum_nachrichten = data["chats"].get(actual_room, [])
    return render_template('chat.html', room=room, nachrichten=raum_nachrichten, partner=chpartner)

@app.route('/chat/<room>/send', methods=['POST'])
def send_message(room):
    if 'username' not in session: return {"error": "Login erforderlich"}, 401
    
    nachricht_text = request.form.get('message', '').strip()
    if not nachricht_text: return {"status": "empty"}, 400
    
    data, sha = load_all_data()
    current_user = session['username']
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    if actual_room not in data["chats"]:
        data["chats"][actual_room] = []
        
    data["chats"][actual_room].append({"name": current_user, "text": nachricht_text})
    save_all_data(data, sha)
    return {"status": "success"}

@app.route('/api/chat-messages/<room>')
def api_chat_messages(room):
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data, sha = load_all_data()
    current_user = session['username']
    
    nachrichten = data["chats"].get(room, [])
    
    # "Gelesen"-Logik nur für private DMs (nicht für den globalen Chat)
    if room != "global":
        # Wer ist der Partner? (Der Raumname ist der Name des Partners)
        partner = room
        room_id = get_private_room_name(current_user, partner)
        nachrichten = data["chats"].get(room_id, [])
        
        # Wir merken uns, dass der aktuelle User alle bisherigen Nachrichten gesehen hat
        if "read_status" not in data:
            data["read_status"] = {}
        if room_id not in data["read_status"]:
            data["read_status"][room_id] = {}
            
        # Speichern, wie viele Nachrichten der aktuelle User jetzt gesehen hat
        data["read_status"][room_id][current_user] = len(nachrichten)
        save_all_data(data, sha) # Direkt auf GitHub sichern
        
        # Jetzt fügen wir für das Frontend die Info hinzu, ob der Partner die Nachricht schon gesehen hat
        partner_seen_count = data["read_status"][room_id].get(partner, 0)
        
        for index, msg in enumerate(nachrichten):
            # Wenn der Index der Nachricht kleiner ist als das, was der Partner gesehen hat -> Gelesen!
            msg["gelesen"] = (index < partner_seen_count)

    return jsonify(nachrichten)


# --- GAME 1: GEOMETRY DASH ---

@app.route('/geometry-dash')
def game():
    if 'username' not in session: return redirect(url_for('login'))
    
    data, _ = load_all_data()
    scores_data = data.get("scores", {})
    
    vollstaendige_liste = [(s, scores_data.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard = sorted(vollstaendige_liste, key=lambda x: x[1], reverse=True)
    return render_template('game.html', leaderboard=leaderboard)
    
@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    score = int(request.json.get('score', 0))
    current_user = session['username']
    
    data, sha = load_all_data()
    old_score = data["scores"].get(current_user, 0)
    if score > old_score:
        data["scores"][current_user] = score
        save_all_data(data, sha)
    return {"status": "success"}


# --- GAME 2: CLICKER GAME ---

@app.route('/clicker')
def clicker_game():
    if 'username' not in session: return redirect(url_for('login'))
    
    data, _ = load_all_data()
    click_data = data.get("clicker_scores", {})
    
    clicker_liste = [(s, click_data.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard = sorted(clicker_liste, key=lambda x: x[1], reverse=True)
    return render_template('clicker.html', leaderboard=leaderboard)

@app.route('/api/submit-clicker', methods=['POST'])
def submit_clicker():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    score = int(request.json.get('score', 0))
    current_user = session['username']
    
    data, sha = load_all_data()
    old_score = data["clicker_scores"].get(current_user, 0)
    if score > old_score:
        data["clicker_scores"][current_user] = score
        save_all_data(data, sha)
    return {"status": "success"}


# --- GAME 3: TIC-TAC-TOE ---

@app.route('/tictactoe')
def tictactoe_menu():
    if 'username' not in session: return redirect(url_for('login'))
    gegner_liste = [s for s in KLASSEN_LISTE if s != session['username']]
    return render_template('tictactoe_menu.html', gegner_liste=gegner_liste)

@app.route('/tictactoe/invite', methods=['POST'])
def tictactoe_invite():
    if 'username' not in session: return redirect(url_for('login'))
    gegner = request.form.get('gegner')
    me = session['username']
    
    data, sha = load_all_data()
    game_id = get_ttt_id(me, gegner)
    
    data["tictactoe"][game_id] = {
        "ersteller": me,
        "gegner": gegner,
        "board": ["", "", "", "", "", "", "", "", ""],
        "turn": me,
        "status": "eingeladen"
    }
    save_all_data(data, sha)
    return redirect(url_for('tictactoe_game', game_id=game_id))

@app.route('/tictactoe/accept/<game_id>', methods=['POST'])
def tictactoe_accept(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    data, sha = load_all_data()
    if game_id in data["tictactoe"]:
        data["tictactoe"][game_id]["status"] = "aktiv"
        save_all_data(data, sha)
    return redirect(url_for('tictactoe_game', game_id=game_id))

@app.route('/tictactoe/game/<game_id>')
def tictactoe_game(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('tictactoe_match.html', game_id=game_id, me=session['username'])

@app.route('/api/tictactoe/status/<game_id>')
def ttt_status(game_id):
    data, _ = load_all_data()
    return json.dumps(data["tictactoe"].get(game_id, {}))

@app.route('/api/tictactoe/move/<game_id>', methods=['POST'])
def ttt_move(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    cell_index = int(request.json.get('cell'))
    me = session['username']
    
    data, sha = load_all_data()
    game = data["tictactoe"].get(game_id)
    
    if game and game["status"] == "aktiv" and game["turn"] == me:
        if game["board"][cell_index] == "":
            zeichen = "X" if me == game["ersteller"] else "O"
            game["board"][cell_index] = zeichen
            game["turn"] = game["gegner"] if me == game["ersteller"] else game["ersteller"]
            
            win_conditions = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]]
            for b in win_conditions:
                if game["board"][b[0]] == game["board"][b[1]] == game["board"][b[2]] != "":
                    game["status"] = f"gewonnen_{me}"
            
            if "" not in game["board"] and "gewonnen" not in game["status"]:
                game["status"] = "unentschieden"
                
            save_all_data(data, sha)
            return {"status": "success"}
            
    return {"status": "invalid_move"}, 400

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
