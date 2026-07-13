import os
from flask import Flask, redirect, render_template, request, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# --- DATENBANK KONFIGURATION (NEON.TECH) ---
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Feste Klassenliste
KLASSEN_LISTE = [
    "Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", 
    "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", "Johann", 
    "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", "Meike",
    "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard",
    "Test Account"
]

# --- DATENBANK MODELLE (TABELLEN) ---

class UserSetting(db.Model):
    __tablename__ = 'user_settings'
    username = db.Column(db.String(50), primary_key=True)
    pin = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room = db.Column(db.String(100), default='global')
    sender = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)

class ChatReadStatus(db.Model):
    __tablename__ = 'chat_read_status'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_id = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    seen_count = db.Column(db.Integer, default=0)

class GameScore(db.Model):
    __tablename__ = 'game_scores'
    username = db.Column(db.String(50), primary_key=True)
    geometry_dash = db.Column(db.Integer, default=0)
    clicker = db.Column(db.Integer, default=0)
    flappy = db.Column(db.Integer, default=-1)
    reaction = db.Column(db.Integer, default=9999)

class TicTacToeGame(db.Model):
    __tablename__ = 'tictactoe_games'
    game_id = db.Column(db.String(100), primary_key=True)
    ersteller = db.Column(db.String(50), nullable=False)
    gegner = db.Column(db.String(50), nullable=False)
    board = db.Column(db.String(50), default=",,,,,,,,") # Als Komma-String für einfaches Splitten
    turn = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="eingeladen")

class TankGame(db.Model):
    __tablename__ = 'tank_games'
    game_id = db.Column(db.String(100), primary_key=True)
    ersteller = db.Column(db.String(50), nullable=False)
    gegner = db.Column(db.String(50), nullable=False)
    # Speichert: player_hp, bot_hp (wird zum gegner_hp), player_x, gegner_x
    state = db.Column(db.String(100), default="100,100,80,620") 
    turn = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="eingeladen")
    last_shot = db.Column(db.String(100), default="") # Speichert den letzten Schuss: "winkel,kraft" für die Animation beim Gegner


# --- HILFSFUNKTIONEN ---

def get_private_room_name(user1, user2):
    return "_".join(sorted([user1, user2]))

def get_ttt_id(p1, p2):
    return f"{min(p1, p2)}_vs_{max(p1, p2)}"

def get_admins_list():
    admins = UserSetting.query.filter_by(is_admin=True).all()
    admin_names = [a.username for a in admins]
    if "Till" not in admin_names:
        admin_names.append("Till")
    return admin_names


# --- ROUTEN ---

@app.before_request
def update_last_seen():
    if 'username' in session:
        user = UserSetting.query.filter_by(username=session['username']).first()
        if user:
            user.last_seen = datetime.utcnow()
            db.session.commit()


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
            
        user = UserSetting.query.filter_by(username=eingabe_name).first()
        
        if user and user.pin:
            if user.pin == eingabe_pin:
                session['username'] = eingabe_name
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', fehler="Falsche PIN! 🤔", name_vorbefuellt=eingabe_name)
        else:
            if len(eingabe_pin) < 4:
                return render_template('login.html', info="Erstelle bitte eine mindestens 4-stellige PIN!", name_vorbefuellt=eingabe_name)
            
            if not user:
                is_till = (eingabe_name == "Till")
                user = UserSetting(username=eingabe_name, pin=eingabe_pin, is_admin=is_till)
                db.session.add(user)
            else:
                user.pin = eingabe_pin
            db.session.commit()
            
            session['username'] = eingabe_name
            return redirect(url_for('dashboard'))
            
    return render_template('login.html')


@app.route('/welcome')
def dashboard():
    if 'username' not in session: 
        return redirect(url_for('login'))
    
    me = session['username']
    aktive_matches = []
    
    # 1. Aktive Tic-Tac-Toe Matches holen
    ttt_games = TicTacToeGame.query.filter(((TicTacToeGame.ersteller == me) | (TicTacToeGame.gegner == me)) & (TicTacToeGame.status == "aktiv")).all()
    for g in ttt_games:
        aktive_matches.append({"id": g.game_id, "von": f"Tic-Tac-Toe vs. {g.gegner if g.ersteller == me else g.ersteller}", "is_active": True, "typ": "tictactoe"})

    # 2. Aktive Tank Royale Matches holen
    tank_games = TankGame.query.filter(((TankGame.ersteller == me) | (TankGame.gegner == me)) & (TankGame.status == "aktiv")).all()
    for g in tank_games:
        aktive_matches.append({"id": g.game_id, "von": f"Tank Royale vs. {g.gegner if g.ersteller == me else g.ersteller}", "is_active": True, "typ": "tankroyale"})

    user = UserSetting.query.filter_by(username=me).first()
    is_admin = True if (me == "Till" or (user and user.is_admin)) else False
    
    return render_template('dashboard.html', name=me, einladungen=aktive_matches, is_admin=is_admin)

@app.route('/api/dashboard-stats')
def dashboard_stats():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    
    global_chat_len = ChatMessage.query.filter_by(room='global').count()
    
    private_chats_stats = {}
    for schueler in KLASSEN_LISTE:
        if schueler != current_user:
            room_id = get_private_room_name(current_user, schueler)
            private_chats_stats[schueler] = ChatMessage.query.filter_by(room=room_id).count()
    
    return {
        "global_messages_count": global_chat_len,
        "private_messages_stats": private_chats_stats
    }

# --- ADMIN PANEL ---
@app.route('/admin')
def admin_panel():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    
    user = UserSetting.query.filter_by(username=me).first()
    is_admin = True if (me == "Till" or (user and user.is_admin)) else False
    if not is_admin:
        return "Zugriff verweigert! ❌ Du bist kein Admin.", 403
        
    all_users = UserSetting.query.all()
    pins_dict = {u.username: u.pin for u in all_users if u.pin}
    admins_list = get_admins_list()
        
    return render_template('admin.html', pins=pins_dict, admins=admins_list, klassen_liste=KLASSEN_LISTE)

@app.route('/admin/make-admin', methods=['POST'])
def make_admin():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    
    neuer_admin = request.form.get('schueler')
    if neuer_admin in KLASSEN_LISTE:
        target_user = UserSetting.query.filter_by(username=neuer_admin).first()
        if not target_user:
            target_user = UserSetting(username=neuer_admin, is_admin=True)
            db.session.add(target_user)
        else:
            target_user.is_admin = True
        db.session.commit()
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove-admin/<schueler>', methods=['POST'])
def remove_admin(schueler):
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    
    if schueler != "Till":
        target_user = UserSetting.query.filter_by(username=schueler).first()
        if target_user:
            target_user.is_admin = False
            db.session.commit()
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset-pin/<schueler>', methods=['POST'])
def admin_reset_pin(schueler):
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    
    target_user = UserSetting.query.filter_by(username=schueler).first()
    if target_user:
        target_user.pin = None
        db.session.commit()
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/clear-chat', methods=['POST'])
def admin_clear_chat():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    
    ChatMessage.query.filter_by(room='global').delete()
    system_msg = ChatMessage(room='global', sender='System', text='Der Chat wurde vom Admin aufgeräumt! 🧹')
    db.session.add(system_msg)
    db.session.commit()
    
    return redirect(url_for('admin_panel'))

# --- CHAT ROUTEN ---

@app.route('/chat')
@app.route('/chat/<room>')
def chat(room="global"):
    if 'username' not in session: return redirect(url_for('login'))

    # In der chat()-Route einfügen:
    zwei_minuten_ago = datetime.utcnow() - timedelta(minutes=2)
    online_users = UserSetting.query.filter(UserSetting.last_seen >= zwei_minuten_ago).all()
    online_names = [u.username for u in online_users]

    
    current_user = session['username']
    chpartner = sorted([schueler for schueler in KLASSEN_LISTE if schueler != current_user])
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    db_messages = ChatMessage.query.filter_by(room=actual_room).order_by(ChatMessage.id.asc()).all()
    raum_nachrichten = [{"name": m.sender, "text": m.text} for m in db_messages]
    
    admins = get_admins_list()
    return render_template('chat.html', room=room, nachrichten=raum_nachrichten, partner=chpartner, admins=admins, online_liste=online_names)

@app.route('/chat/<room>/send', methods=['POST'])
def send_message(room):
    if 'username' not in session: return {"error": "Login erforderlich"}, 401
    
    nachricht_text = request.form.get('message', '').strip()
    if not nachricht_text: return {"status": "empty"}, 400
    
    current_user = session['username']
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    new_msg = ChatMessage(room=actual_room, sender=current_user, text=nachricht_text)
    db.session.add(new_msg)
    db.session.commit()
    return {"status": "success"}

@app.route('/api/chat-messages/<room>')
def api_chat_messages(room):
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    
    actual_room = room
    if room != "global":
        partner = room
        actual_room = get_private_room_name(current_user, partner)
        
        db_messages = ChatMessage.query.filter_by(room=actual_room).order_by(ChatMessage.id.asc()).all()
        total_msg_count = len(db_messages)
        
        status_rec = ChatReadStatus.query.filter_by(room_id=actual_room, username=current_user).first()
        if not status_rec:
            status_rec = ChatReadStatus(room_id=actual_room, username=current_user, seen_count=total_msg_count)
            db.session.add(status_rec)
        else:
            status_rec.seen_count = total_msg_count
        db.session.commit()
        
        partner_rec = ChatReadStatus.query.filter_by(room_id=actual_room, username=partner).first()
        partner_seen_count = partner_rec.seen_count if partner_rec else 0
        
        nachrichten = []
        for index, m in enumerate(db_messages):
            nachrichten.append({
                "name": m.sender,
                "text": m.text,
                "gelesen": (index < partner_seen_count)
            })
        return jsonify(nachrichten)
        
    db_messages = ChatMessage.query.filter_by(room='global').order_by(ChatMessage.id.asc()).all()
    return jsonify([{"name": m.sender, "text": m.text} for m in db_messages])

@app.route('/chat/<room>/delete/<int:msg_index>', methods=['POST'])
def delete_message(room, msg_index):
    if 'username' not in session: 
        return redirect(url_for('login'))
        
    current_user = session['username']
    
    # 1. ADMIN-LISTE HOEN:
    # Falls du 'admins' global definiert hast, brauchst du diese Zeile nicht.
    # Wenn sie aus der DB kommt oder oben in der app.py steht, passe sie kurz an.
    # Beispiel: admins = ["DeinName", "AdminZwei"] 
    
    actual_room = room
    if room != "global":
        actual_room = get_private_room_name(current_user, room)
        
    db_messages = ChatMessage.query.filter_by(room=actual_room).order_by(ChatMessage.id.asc()).all()
    
    if 0 <= msg_index < len(db_messages):
        target_msg = db_messages[msg_index]
        
        # 2. BERECHTIGUNG PRÜFEN: Eigener Absender ODER der User ist Admin
        if target_msg.sender == current_user or current_user in admins:
            db.session.delete(target_msg)
            db.session.commit()
                
    return redirect(url_for('chat', room=room))

# --- GAMES & LEADERBOARDS ---

@app.route('/games')
def games_menu():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    
    # 1. Tic-Tac-Toe Einladungen holen
    ttt_invites = TicTacToeGame.query.filter_by(gegner=me, status='eingeladen').all()
    aktive_einladungen = [{"id": i.game_id, "von": i.ersteller, "typ": "tictactoe"} for i in ttt_invites]
    
    # 2. HIER WAR DER FEHLER: Tank Royale Einladungen wurden ignoriert!
    tank_invites = TankGame.query.filter_by(gegner=me, status='eingeladen').all()
    for i in tank_invites:
        aktive_einladungen.append({"id": i.game_id, "von": i.ersteller, "typ": "tankroyale"})
            
    return render_template('games.html', einladungen=aktive_einladungen)
@app.route('/geometry-dash')
def game():
    if 'username' not in session: return redirect(url_for('login'))
    
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.geometry_dash for s in all_scores}
    
    vollstaendige_liste = [(s, scores_dict.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard = sorted(vollstaendige_liste, key=lambda x: x[1], reverse=True)
    return render_template('geometry_dash.html', leaderboard=leaderboard)
    
@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    score = int(request.json.get('score', 0))
    current_user = session['username']
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score:
        user_score = GameScore(username=current_user, geometry_dash=score)
        db.session.add(user_score)
    elif score > user_score.geometry_dash:
        user_score.geometry_dash = score
    db.session.commit()
    return {"status": "success"}

@app.route('/clicker')
def clicker_game():
    if 'username' not in session: return redirect(url_for('login'))
    
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.clicker for s in all_scores}
    
    leaderboard_data = [(s, scores_dict.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard_sorted = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)
    return render_template('clicker.html', leaderboard=leaderboard_sorted)

@app.route('/api/submit-clicker', methods=['POST'])
def submit_clicker():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    score = int(request.json.get('score', 0))
    current_user = session['username']
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score:
        user_score = GameScore(username=current_user, clicker=score)
        db.session.add(user_score)
    elif score > user_score.clicker:
        user_score.clicker = score
    db.session.commit()
    return {"status": "success"}

@app.route('/flappy')
def flappy_game():
    if 'username' not in session: return redirect(url_for('login'))
    
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.flappy for s in all_scores}
    
    leaderboard_data = [(s, scores_dict.get(s, 0)) for s in KLASSEN_LISTE]
    leaderboard = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)
    return render_template('flappy.html', leaderboard=leaderboard)

@app.route('/api/submit-flappy', methods=['POST'])
def submit_flappy():
    if 'username' not in session: return {"error": "401"}, 401
    user = session['username']
    val = request.json.get('score', 0)
    
    user_score = GameScore.query.filter_by(username=user).first()
    if not user_score:
        user_score = GameScore(username=user, flappy=val)
        db.session.add(user_score)
    elif val > user_score.flappy:
        user_score.flappy = val
    db.session.commit()
    return {"status": "ok"}

@app.route('/reaction')
def reaction_game():
    if 'username' not in session: return redirect(url_for('login'))
    
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.reaction for s in all_scores}
    
    leaderboard_data = [(s, scores_dict.get(s, 9999)) for s in KLASSEN_LISTE]
    leaderboard = sorted(leaderboard_data, key=lambda x: x[1], reverse=False)
    return render_template('reaction.html', leaderboard=leaderboard)

@app.route('/api/submit-reaction', methods=['POST'])
def submit_reaction():
    if 'username' not in session: return {"error": "401"}, 401
    user = session['username']
    val = request.json.get('score', 9999)
    
    user_score = GameScore.query.filter_by(username=user).first()
    if not user_score:
        user_score = GameScore(username=user, reaction=val)
        db.session.add(user_score)
    elif val < user_score.reaction:
        user_score.reaction = val
    db.session.commit()
    return {"status": "ok"}

# --- TIC-TAC-TOE ---

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
    
    game_id = get_ttt_id(me, gegner)
    existing = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if existing:
        db.session.delete(existing)
    
    new_game = TicTacToeGame(
        game_id=game_id, ersteller=me, gegner=gegner,
        board=", , , , , , , , ", turn=me, status="eingeladen"
    )
    db.session.add(new_game)
    db.session.commit()
    return redirect(url_for('tictactoe_game', game_id=game_id))

@app.route('/tictactoe/accept/<game_id>', methods=['POST'])
def tictactoe_accept(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g:
        g.status = "aktiv"
        db.session.commit()
    return redirect(url_for('tictactoe_game', game_id=game_id))

@app.route('/tictactoe/decline/<game_id>', methods=['POST'])
def tictactoe_decline(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g:
        db.session.delete(g)
        db.session.commit()
    return redirect(url_for('games_menu'))

@app.route('/tictactoe/delete-match/<game_id>', methods=['POST'])
def delete_match(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g:
        db.session.delete(g)
        db.session.commit()
    return redirect(url_for('dashboard'))

# --- PAUSIEREN & RESUMEN (NEU) ---

@app.route('/api/tictactoe/pause/<game_id>', methods=['POST'])
def tictactoe_pause(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g and (session['username'] in [g.ersteller, g.gegner]):
        g.status = "pausiert"
        db.session.commit()
        return {"status": "paused"}
    return {"error": "Match nicht gefunden oder keine Rechte"}, 400

@app.route('/api/tictactoe/resume/<game_id>', methods=['POST'])
def tictactoe_resume(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g and (session['username'] in [g.ersteller, g.gegner]):
        g.status = "aktiv"
        db.session.commit()
        return {"status": "resumed"}
    return {"error": "Match nicht gefunden oder keine Rechte"}, 400


@app.route('/tictactoe/game/<game_id>')
def tictactoe_game(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('tictactoe_match.html', game_id=game_id, me=session['username'])

@app.route('/api/tictactoe/status/<game_id>')
def ttt_status(game_id):
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g:
        raw_board = g.board.split(',')
        cleaned_board = [cell.strip() for cell in raw_board]
        return jsonify({
            "ersteller": g.ersteller, "gegner": g.gegner,
            "board": cleaned_board, "turn": g.turn, "status": g.status
        })
    return jsonify({})

@app.route('/api/tictactoe/move/<game_id>', methods=['POST'])
def ttt_move(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    cell_index = int(request.json.get('cell'))
    me = session['username']
    
    g = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if g and g.status == "aktiv" and g.turn == me:
        board_list = [c.strip() for c in g.board.split(',')]
        if board_list[cell_index] == "":
            zeichen = "X" if me == g.ersteller else "O"
            board_list[cell_index] = zeichen
            g.board = ",".join(board_list)
            g.turn = g.gegner if me == g.ersteller else g.ersteller
            
            win_conditions = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]]
            for b in win_conditions:
                if board_list[b[0]] == board_list[b[1]] == board_list[b[2]] != "":
                    g.status = f"gewonnen_{me}"
            
            if "" not in board_list and "gewonnen" not in g.status:
                g.status = "unentschieden"
                
            db.session.commit()
            return {"status": "success"}
            
    return {"status": "invalid_move"}, 400

# --- TANK ROYALE MULTIPLAYER ---

@app.route('/tankroyale')
def tankroyale_menu():
    if 'username' not in session: return redirect(url_for('login'))
    gegner_liste = sorted([s for s in KLASSEN_LISTE if s != session['username']])
    return render_template('tank_royale_menu.html', gegner_liste=gegner_liste)

@app.route('/tankroyale/invite', methods=['POST'])
def tankroyale_invite():
    if 'username' not in session: return redirect(url_for('login'))
    gegner = request.form.get('gegner')
    me = session['username']
    
    game_id = f"{min(me, gegner)}_tank_{max(me, gegner)}"
    existing = TankGame.query.filter_by(game_id=game_id).first()
    if existing:
        db.session.delete(existing)
    
    new_game = TankGame(
        game_id=game_id, ersteller=me, gegner=gegner,
        state="100,100,80,620", turn=me, status="eingeladen"
    )
    db.session.add(new_game)
    db.session.commit()
    return redirect(url_for('tankroyale_match', game_id=game_id))

@app.route('/tankroyale/accept/<game_id>', methods=['POST'])
def tankroyale_accept(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    g = TankGame.query.filter_by(game_id=game_id).first()
    if g:
        g.status = "aktiv"
        db.session.commit()
    return redirect(url_for('tankroyale_match', game_id=game_id))

@app.route('/tankroyale/decline/<game_id>', methods=['POST'])
def tankroyale_decline(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    g = TankGame.query.filter_by(game_id=game_id).first()
    if g:
        db.session.delete(g)
        db.session.commit()
    return redirect(url_for('games_menu'))

@app.route('/tankroyale/match/<game_id>')
def tankroyale_match(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('tank_royale_match.html', gameId=game_id, me=session['username'])

@app.route('/api/tankroyale/status/<game_id>')
def tank_status(game_id):
    g = TankGame.query.filter_by(game_id=game_id).first()
    if g:
        state_list = [int(x) for x in g.state.split(',')]
        return jsonify({
            "ersteller": g.ersteller, "gegner": g.gegner,
            "p1_hp": state_list[0], "p2_hp": state_list[1],
            "p1_x": state_list[2], "p2_x": state_list[3],
            "turn": g.turn, "status": g.status, "last_shot": g.last_shot
        })
    return jsonify({})

@app.route('/api/tankroyale/shoot/<game_id>', methods=['POST'])
def tank_shoot(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    me = session['username']
    angle = float(request.json.get('angle'))
    power = float(request.json.get('power'))
    hit = request.json.get('hit') # 'p1', 'p2' oder 'none'
    
    g = TankGame.query.filter_by(game_id=game_id).first()
    if g and g.status == "aktiv" and g.turn == me:
        state_list = [int(x) for x in g.state.split(',')]
        
        # Treffer verrechnen (Schaden = 35 HP)
        if hit == "p1":
            state_list[0] = max(0, state_list[0] - 35)
        elif hit == "p2":
            state_list[1] = max(0, state_list[1] - 35)
            
        g.state = f"{state_list[0]},{state_list[1]},{state_list[2]},{state_list[3]}"
        g.last_shot = f"{angle},{power}"
        
        # Prüfen ob jemand tot ist
        if state_list[0] <= 0:
            g.status = f"gewonnen_{g.gegner}"
        elif state_list[1] <= 0:
            g.status = f"gewonnen_{g.ersteller}"
        else:
            # Rundenwechsel
            g.turn = g.gegner if me == g.ersteller else g.ersteller
            
        db.session.commit()
        return {"status": "success"}
        
    return {"status": "invalid_move"}, 400

@app.route('/tankroyale/delete-match/<game_id>', methods=['POST'])
def tankroyale_delete_match(game_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Match aus der Datenbank suchen
    match = TankGame.query.filter_by(game_id=game_id).first()
    
    if match:
        db.session.delete(match)
        db.session.commit()
        
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- ERZWINGT DAS ERSTELLEN BEIM LADEN DER DATEI ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
