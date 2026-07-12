import base64
import json
import os
import requests
from flask import Flask, redirect, render_template, request, session, url_for, jsonify

app = Flask(__name__)
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
        return {"chats": {"global": []}, "scores": {}, "clicker_scores": {}, "flappy_scores": {}, "reaction_scores": {}, "pins": {}, "tictactoe": {}, "admins": ["Till"]}, None
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            parsed_data = json.loads(content)
            
            if "chats" not in parsed_data: parsed_data["chats"] = {"global": []}
            if "scores" not in parsed_data: parsed_data["scores"] = {}
            if "clicker_scores" not in parsed_data: parsed_data["clicker_scores"] = {}
            if "flappy_scores" not in parsed_data: parsed_data["flappy_scores"] = {}
            if "reaction_scores" not in parsed_data: parsed_data["reaction_scores"] = {}
            if "pins" not in parsed_data: parsed_data["pins"] = {}
            if "tictactoe" not in parsed_data: parsed_data["tictactoe"] = {}
            
            # NEU: Falls noch keine Admin-Struktur existiert, bist du der Standard-Admin
            if "admins" not in parsed_data: 
                parsed_data["admins"] = ["Till"]
            elif "Till" not in parsed_data["admins"]:
                parsed_data["admins"].append("Till") # Sicherheitshalber bist du immer drin
                
            return parsed_data, file_data['sha']
        else:
            return {"chats": {"global": []}, "scores": {}, "clicker_scores": {}, "flappy_scores": {}, "reaction_scores": {}, "pins": {}, "tictactoe": {}, "admins": ["Till"]}, None
    except Exception:
        return {"chats": {"global": []}, "scores": {}, "clicker_scores": {}, "flappy_scores": {}, "reaction_scores": {}, "pins": {}, "tictactoe": {}, "admins": ["Till"]}, None

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

@app.route('/games')
def games_menu():
    if 'username' not in session: 
        return redirect(url_for('login'))
    
    data, _ = load_all_data()
    ttt_games = data.get("tictactoe", {})
    me = session['username']
    
    aktive_einladungen = []
    for g_id, g_data in ttt_games.items():
        if g_data["gegner"] == me and g_data["status"] == "eingeladen":
            aktive_einladungen.append({"id": g_id, "von": g_data["ersteller"]})
            
    return render_template('games.html', einladungen=aktive_einladungen)

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
                return render_template('login.html', fehler="Falsche PIN! 🤔", name_vorbefuellt=eingabe_name)
        else:
            if len(eingabe_pin) < 4:
                return render_template('login.html', info="Erstelle bitte eine mindestens 4-stellige PIN!", name_vorbefuellt=eingabe_name)
            
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
    
    aktive_matches = []
    for g_id, g_data in ttt_games.items():
        if (g_data["ersteller"] == me or g_data["gegner"] == me) and g_data["status"] == "aktiv":
            aktive_matches.append({"id": g_id, "von": "Dein Match läuft!", "is_active": True})

    # DYNAMISCH: Prüft, ob du in der Admin-Liste stehst
    is_admin = (me in data.get("admins", ["Till"]))
    return render_template('dashboard.html', name=me, einladungen=aktive_matches, is_admin=is_admin)

@app.route('/api/dashboard-stats')
def dashboard_stats():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data, _ = load_all_data()
    current_user = session['username']
    
    global_chat_len = len(data["chats"].get("global", []))
    
    private_chats_stats = {}
    for schueler in KLASSEN_LISTE:
        if schueler != current_user:
            room_id = get_private_room_name(current_user, schueler)
            private_chats_stats[schueler] = len(data["chats"].get(room_id, []))
    
    return {
        "global_messages_count": global_chat_len,
        "private_messages_stats": private_chats_stats
    }

# --- 🛠️ DAS DYNAMISCHE ADMIN PANEL ROUTEN ---
@app.route('/admin')
def admin_panel():
    if 'username' not in session: return redirect(url_for('login'))
    data, _ = load_all_data()
    
    # Prüfen, ob der User Admin-Rechte besitzt
    if session['username'] not in data.get("admins", ["Till"]):
        return "Zugriff verweigert! ❌ Du bist kein Admin.", 403
        
    return render_template('admin.html', pins=data.get("pins", {}), admins=data.get("admins", []), klassen_liste=KLASSEN_LISTE)

# NEU: Route um jemanden zum Admin zu machen
@app.route('/admin/make-admin', methods=['POST'])
def make_admin():
    if 'username' not in session: return "403", 403
    data, sha = load_all_data()
    
    if session['username'] not in data.get("admins", ["Till"]): return "403", 403
    
    neuer_admin = request.form.get('schueler')
    if neuer_admin in KLASSEN_LISTE and neuer_admin not in data["admins"]:
        data["admins"].append(neuer_admin)
        save_all_data(data, sha)
        
    return redirect(url_for('admin_panel'))

# NEU: Route um jemanden als Admin zu entfernen
@app.route('/admin/remove-admin/<schueler>', methods=['POST'])
def remove_admin(schueler):
    if 'username' not in session: return "403", 403
    data, sha = load_all_data()
    
    if session['username'] not in data.get("admins", ["Till"]): return "403", 403
    
    # "Till" darf sich zur Sicherheit nicht selbst löschen!
    if schueler in data["admins"] and schueler != "Till":
        data["admins"].remove(schueler)
        save_all_data(data, sha)
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset-pin/<schueler>', methods=['POST'])
def admin_reset_pin(schueler):
    if 'username' not in session: return "403", 403
    data, sha = load_all_data()
    
    if session['username'] not in data.get("admins", ["Till"]): return "403", 403
    
    if schueler in data["pins"]:
        del data["pins"][schueler]
        save_all_data(data, sha)
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/clear-chat', methods=['POST'])
def admin_clear_chat():
    if 'username' not in session: return "403", 403
    data, sha = load_all_data()
    
    if session['username'] not in data.get("admins", ["Till"]): return "403", 403
    
    data["chats"]["global"] = [{"name": "System", "text": "Der Chat wurde vom Admin aufgeräumt! 🧹"}]
    save_all_data(data, sha)
    
    return redirect(url_for('admin_panel'))

# --- CHAT ROUTEN ---

@app.route('/chat')
@app.route('/chat/<room>')
def chat(room="global"):
    if 'username' not in session: return redirect(url_for('login'))
    
    data, _ = load_all_data()
    current_user = session['username']
    chpartner = sorted([schueler for schueler in KLASSEN_LISTE if schueler != current_user])
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    raum_nachrichten = data["chats"].get(actual_room, [])
    
    # NEU: Wir holen uns die Admin-Liste aus den Daten (Standard: Till)
    aktuelle_admins = data.get("admins", ["Till"])
    
    return render_template('chat.html', room=room, nachrichten=raum_nachrichten, partner=chpartner, admins=aktuelle_admins)

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
    
    if room != "global":
        partner = room
        room_id = get_private_room_name(current_user, partner)
        nachrichten = data["chats"].get(room_id, [])
        
        if "read_status" not in data: data["read_status"] = {}
        if room_id not in data["read_status"]: data["read_status"][room_id] = {}
            
        data["read_status"][room_id][current_user] = len(nachrichten)
        save_all_data(data, sha)
        
        partner_seen_count = data["read_status"][room_id].get(partner, 0)
        for index, msg in enumerate(nachrichten):
            msg["gelesen"] = (index < partner_seen_count)

    return jsonify(nachrichten)

@app.route('/chat/<room>/delete/<int:msg_index>', methods=['POST'])
def delete_message(room, msg_index):
    if 'username' not in session: return redirect(url_for('login'))
    
    data, sha = load_all_data()
    current_user = session['username']
    
    if room == "global":
        room_id = "global"
    else:
        room_id = get_private_room_name(current_user, room)
        
    if room_id in data["chats"]:
        nachrichten = data["chats"][room_id]
        if 0 <= msg_index < len(nachrichten):
            if nachrichten[msg_index]["name"] == current_user:
                nachrichten.pop(msg_index)
                save_all_data(data, sha)
                
    return redirect(url_for('chat', room=room))

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
    scores = data.get("clicker_scores", {})
    
    leaderboard_data = []
    for schueler in KLASSEN_LISTE:
        schueler_score = scores.get(schueler, 0)
        leaderboard_data.append((schueler, schueler_score))
        
    leaderboard_sorted = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)
    return render_template('clicker.html', leaderboard=leaderboard_sorted)

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
    gegner_liste = sorted([s for s in KLASSEN_LISTE if s != session['username']])
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

@app.route('/tictactoe/decline/<game_id>', methods=['POST'])
def tictactoe_decline(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    data, sha = load_all_data()
    if "tictactoe" in data and game_id in data["tictactoe"]:
        del data["tictactoe"][game_id]
        save_all_data(data, sha)
    return redirect(url_for('games_menu'))

@app.route('/tictactoe/delete-match/<game_id>', methods=['POST'])
def delete_match(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    data, sha = load_all_data()
    if "tictactoe" in data and game_id in data["tictactoe"]:
        del data["tictactoe"][game_id]
        save_all_data(data, sha)
    return redirect(url_for('dashboard'))

@app.route('/tictactoe/game/<game_id>')
def tictactoe_game(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('tictactoe_match.html', game_id=game_id, me=session['username'])

@app.route('/api/tictactoe/status/<game_id>')
def ttt_status(game_id):
    data, _ = load_all_data()
    return jsonify(data["tictactoe"].get(game_id, {}))

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

# --- 🦘 FLAPPY BIRD ROUTES ---
@app.route('/flappy')
def flappy_game():
    if 'username' not in session: return redirect(url_for('login'))
    data, _ = load_all_data()
    scores = data.get("flappy_scores", {})
    
    leaderboard_data = [(s, scores.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)
    return render_template('flappy.html', leaderboard=leaderboard)

@app.route('/api/submit-flappy', methods=['POST'])
def submit_flappy():
    if 'username' not in session: return {"error": "401"}, 401
    user = session['username']
    val = request.json.get('score', 0)
    
    data, sha = load_all_data()
    if "flappy_scores" not in data: data["flappy_scores"] = {}
    
    if val > data["flappy_scores"].get(user, -1):
        data["flappy_scores"][user] = val
        save_all_data(data, sha)
    return {"status": "ok"}

# --- ⏱️ REFLEX-TEST ROUTES ---
@app.route('/reaction')
def reaction_game():
    if 'username' not in session: return redirect(url_for('login'))
    data, _ = load_all_data()
    scores = data.get("reaction_scores", {})
    
    leaderboard_data = [(s, scores.get(s, 9999)) for s in KLASSEN_LISTE]
    leaderboard = sorted(leaderboard_data, key=lambda x: x[1], reverse=False)
    return render_template('reaction.html', leaderboard=leaderboard)

@app.route('/api/submit-reaction', methods=['POST'])
def submit_reaction():
    if 'username' not in session: return {"error": "401"}, 401
    user = session['username']
    val = request.json.get('score', 9999)
    
    data, sha = load_all_data()
    if "reaction_scores" not in data: data["reaction_scores"] = {}
    
    if val < data["reaction_scores"].get(user, 9999):
        data["reaction_scores"][user] = val
        save_all_data(data, sha)
    return {"status": "ok"}

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
