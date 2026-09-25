import os
import random
import uuid
import time
import json
import math
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, redirect, render_template, request, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

# --- DATENBANK KONFIGURATION (NEON.TECH) ---
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Wir schneiden das Protokoll ab, egal was Vercel liefert...
    if "://" in db_url:
        rest_der_url = db_url.split("://", 1)[1]
        # ...und zwingen SQLAlchemy, exakt unseren installierten psycopg2-Treiber zu nehmen!
        db_url = f"postgresql+psycopg2://{rest_der_url}"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local_portal.db'

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Verhindert Verbindungsabbrüche (SSL closed unexpectedly) ---
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)

# RAM-Speicher
last_active = {}
user_activities = {}

# --- SHOP ITEMS ---
SHOP_ITEMS = {
    "title_destroyer": {"id": "title_destroyer", "type": "title", "name": "Titel: Der Zerstörer", "desc": "Ein bedrohlicher Titel im Chat.", "price": 250, "value": "Der Zerstörer"},
    "title_king": {"id": "title_king", "type": "title", "name": "Titel: King", "desc": "Zeig allen, wer der Boss ist.", "price": 500, "value": "King"},
    
    # --- NEUE COOLE TITEL (kaufbar) ---
    "title_vip": {"id": "title_vip", "type": "title", "name": "Titel: VIP", "desc": "Nur für echte Very Important Player.", "price": 800, "value": "VIP"},
    "title_ninja": {"id": "title_ninja", "type": "title", "name": "Titel: Ninja", "desc": "Lautlos und tödlich.", "price": 400, "value": "Ninja"},
    "title_hacker": {"id": "title_hacker", "type": "title", "name": "Titel: Hacker", "desc": "Du kennst den Code.", "price": 600, "value": "Hacker"},
    
    # --- RANG TITEL (rank_only hinzugefügt!) ---
    "title_profi": {"id": "title_profi", "type": "title", "name": "Titel: Profi", "desc": "Belohnung für Level 20.", "price": 0, "value": "Profi", "rank_only": True},
    "title_meister": {"id": "title_meister", "type": "title", "name": "Titel: Meister", "desc": "Belohnung für Level 30.", "price": 0, "value": "Meister", "rank_only": True},
    "title_grossmeister": {"id": "title_grossmeister", "type": "title", "name": "Titel: Großmeister", "desc": "Belohnung für Level 40.", "price": 0, "value": "Großmeister", "rank_only": True},
    "title_legend": {"id": "title_legend", "type": "title", "name": "Titel: Legende", "desc": "Exklusiver Titel für Level 50.", "price": 0, "value": "Legende", "rank_only": True},
    "title_mythos": {"id": "title_mythos", "type": "title", "name": "Titel: Mythos", "desc": "Belohnung für Level 65.", "price": 0, "value": "Mythos", "rank_only": True},
    "title_titan": {"id": "title_titan", "type": "title", "name": "Titel: Titan", "desc": "Belohnung für Level 80.", "price": 0, "value": "Titan", "rank_only": True},
    "title_halbgott": {"id": "title_halbgott", "type": "title", "name": "Titel: Halbgott", "desc": "Belohnung für Level 90.", "price": 0, "value": "Halbgott", "rank_only": True},
    "title_universum": {"id": "title_universum", "type": "title", "name": "Titel: Universum-Beherrscher", "desc": "Der ultimative Rang! Level 100.", "price": 0, "value": "Universum-Beherrscher", "rank_only": True},
    
    "color_gold": {"id": "color_gold", "type": "color", "name": "Name: Gold", "desc": "Dein Name leuchtet Gold.", "price": 300, "value": "#f1c40f"},
    "color_rainbow": {"id": "color_rainbow", "type": "color", "name": "Name: Regenbogen", "desc": "Bunter Chat-Name!", "price": 800, "value": "rainbow"},
    "color_neon": {"id": "color_neon", "type": "color", "name": "Name: Neon Cyan", "desc": "Helles Hacker-Blau.", "price": 300, "value": "#00adb5"},
    
    # --- NEUE COOLE FARBEN (kaufbar) ---
    "color_blood": {"id": "color_blood", "type": "color", "name": "Name: Blood Red", "desc": "Dunkelrot wie Blut.", "price": 400, "value": "#8a0303"},
    "color_toxic": {"id": "color_toxic", "type": "color", "name": "Name: Toxic Green", "desc": "Giftiges, leuchtendes Grün.", "price": 350, "value": "#39ff14"},
    "color_pink": {"id": "color_pink", "type": "color", "name": "Name: Hot Pink", "desc": "Auffällig und stylisch.", "price": 300, "value": "#ff66cc"},
    
    "title_admin": {"id": "title_admin", "type": "title", "name": "Titel: Admin", "desc": "Offizieller Admin-Titel.", "price": 0, "value": "Admin", "admin_only": True},
    "title_crown": {"id": "title_crown", "type": "title", "name": "Titel: Krone", "desc": "Das Zeichen des Bosses.", "price": 0, "value": "👑", "admin_only": True},
    "color_purple": {"id": "color_purple", "type": "color", "name": "Name: Admin Lila", "desc": "Die Admin-Farbe.", "price": 0, "value": "#9b59b6", "admin_only": True},
    
    "upg_snake_life": {"id": "upg_snake_life", "type": "upgrade", "name": "Snake: Extra Leben", "desc": "Du kannst 1x pro Runde eine Wand berühren, ohne zu sterben.", "price": 1000, "value": "snake_life"},
    "upg_brick_fire": {"id": "upg_brick_fire", "type": "upgrade", "name": "BrickBreaker: Feuerball", "desc": "Dein Ball zerstört beim Start Blöcke sofort ohne abzuprallen.", "price": 1200, "value": "brick_fire"},
    "upg_slither_boost": {"id": "upg_slither_boost", "type": "upgrade", "name": "Slither: Sprint-Boost", "desc": "Verliere weniger Punkte, wenn du boostest.", "price": 1500, "value": "slither_boost"}

    # --- NAMENS-AUREN (Nur durch Spielzeit erspielbar, extrem schwer!) ---
    # 1 Stunde = 3600 Spielzeit-Punkte (Ping alle 5 Sek.)
    "aura_fire": {"id": "aura_fire", "type": "color", "name": "🔥 Feuer-Aura", "desc": "Freigeschaltet ab 10 Stunden Spielzeit!", "price": 0, "value": "aura_fire", "playtime_req": 36000},
    "aura_lightning": {"id": "aura_lightning", "type": "color", "name": "⚡ Blitz-Aura", "desc": "Freigeschaltet ab 25 Stunden Spielzeit!", "price": 0, "value": "aura_lightning", "playtime_req": 90000},
    "aura_galaxy": {"id": "aura_galaxy", "type": "color", "name": "🌌 Galaxie-Aura", "desc": "Freigeschaltet ab 50 Stunden Spielzeit!", "price": 0, "value": "aura_galaxy", "playtime_req": 180000},

    # --- LOOTBOXEN (Kaufbar) ---
    "box_common": {"id": "box_common", "type": "lootbox", "name": "📦 Gewöhnliche Kiste", "desc": "Chance auf XP, Coins oder Standard-Items.", "price": 100},
    "box_epic": {"id": "box_epic", "type": "lootbox", "name": "🎁 Epische Kiste", "desc": "Hohe Chance auf seltene Titel und dicke Gewinne!", "price": 400},
}

# --- SLITHER.IO RAM-SPEICHER ---
SLITHER_STATE = {
    "players": {},
    "bots": {},
    "food": {},
    "map_size": 3000
}

COLORS = ["#ff2e63", "#00adb5", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22", "#ffffff", "#e74c3c"]

def spawn_food(amount=10):
    for _ in range(amount):
        fid = str(uuid.uuid4())[:8]
        SLITHER_STATE["food"][fid] = {
            'x': random.randint(100, SLITHER_STATE["map_size"] - 100),
            'y': random.randint(100, SLITHER_STATE["map_size"] - 100),
            'c': random.choice(COLORS),
            'v': 1
        }

spawn_food(150)

for i in range(3):
    SLITHER_STATE["bots"][f"Bot {i+1}"] = {
        "body": [[random.randint(500, 2500), random.randint(500, 2500)]],
        "color": random.choice(COLORS),
        "score": 50,
        "angle": random.uniform(0, math.pi * 2),
        "x": 0, "y": 0
    }

# --- GEHEIMCODES ---
GEHEIME_CODES = {
    "TILLISTDERBESTEADMIN": "double_score",
    "REICHTUM": "1000_coins",
    "ESREGNETMÜNZEN": "100_coins",
    "WHEELXP": "100_xp",
    "ISLIEBEGAMBLING": "150_coins"
}

# --- DATENBANK MODELLE ---
class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)

class AdminMessage(db.Model):
    __tablename__ = 'admin_messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class UserSetting(db.Model):
    __tablename__ = 'user_settings'
    username = db.Column(db.String(50), primary_key=True)
    display_name = db.Column(db.String(50), nullable=True)
    pin = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    banned_until = db.Column(db.DateTime, nullable=True)
    playtime_total = db.Column(db.Integer, default=0)
    score_multiplier = db.Column(db.Integer, default=1)  
    xp = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    inventory = db.Column(db.Text, default='[]')
    active_title = db.Column(db.Text, default='[]')
    active_color = db.Column(db.String(50), nullable=True)
    last_daily_claim = db.Column(db.DateTime, nullable=True)
    login_streak = db.Column(db.Integer, default=0)
    achievements = db.Column(db.Text, default='[]')
    klasse = db.Column(db.String(50), nullable=True)

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
    snake = db.Column(db.Integer, default=0)
    crossy = db.Column(db.Integer, default=0)
    doodle = db.Column(db.Integer, default=0)
    brickbreaker = db.Column(db.Integer, default=0)
    speedtyping = db.Column(db.Integer, default=0)
    slither = db.Column(db.Integer, default=0)
    tower = db.Column(db.Integer, default=0)
    dino = db.Column(db.Integer, default=0)
    
    playtime_gd = db.Column(db.Integer, default=0)
    playtime_clicker = db.Column(db.Integer, default=0)
    playtime_flappy = db.Column(db.Integer, default=0)
    playtime_reaction = db.Column(db.Integer, default=0)
    playtime_snake = db.Column(db.Integer, default=0)
    playtime_crossy = db.Column(db.Integer, default=0)
    playtime_doodle = db.Column(db.Integer, default=0)
    playtime_brickbreaker = db.Column(db.Integer, default=0)
    playtime_speedtyping = db.Column(db.Integer, default=0)
    playtime_slither = db.Column(db.Integer, default=0)
    playtime_tower = db.Column(db.Integer, default=0)
    playtime_dino = db.Column(db.Integer, default=0)

class TicTacToeGame(db.Model):
    __tablename__ = 'tictactoe_games'
    game_id = db.Column(db.String(100), primary_key=True)
    ersteller = db.Column(db.String(50), nullable=False)
    gegner = db.Column(db.String(50), nullable=False)
    board = db.Column(db.String(50), default=",,,,,,,,") 
    turn = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="eingeladen")

class TankGame(db.Model):
    __tablename__ = 'tank_games'
    game_id = db.Column(db.String(100), primary_key=True)
    ersteller = db.Column(db.String(50), nullable=False)
    gegner = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(100), default="100,100,80,620") 
    turn = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="eingeladen")
    last_shot = db.Column(db.String(100), default="") 
    terrain = db.Column(db.Text, nullable=True)

class RedeemedCode(db.Model):
    __tablename__ = 'redeemed_codes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(50), nullable=False)

class SchoolClass(db.Model):
    __tablename__ = 'school_classes'
    name = db.Column(db.String(50), primary_key=True)

class AllowedStudent(db.Model):
    __tablename__ = 'allowed_students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)


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

def get_user_multiplier(username):
    user = UserSetting.query.filter_by(username=username).first()
    if user and user.score_multiplier:
        return user.score_multiplier
    return 1

# --- NEU: Faireres Level-System bis Level 100 ---
def get_level_info(xp):
    xp = xp or 0
    # Neue Formel: Schneller am Anfang, fairer Grind am Ende. (Wurzel aus XP/20)
    level = max(1, math.floor((xp / 12.5) ** 0.5) + 1)
    level = min(100, level)  # Maximal Level 100
    
    if level < 10: rank = "Rookie"
    elif level < 20: rank = "Amateur"
    elif level < 30: rank = "Profi"
    elif level < 40: rank = "Meister"
    elif level < 50: rank = "Großmeister"
    elif level < 65: rank = "Legende"
    elif level < 80: rank = "Mythos"
    elif level < 90: rank = "Titan"
    elif level < 100: rank = "Halbgott"
    else: rank = "Universum-Beherrscher"
    
    return level, rank

# --- NEU: Automatische Titel-Vergabe für alle guten Ränge ---
def check_rank_titles(user):
    if not user: 
        return
        
    lvl, rank = get_level_info(user.xp)
    
    # Liste aller Titel, die der Spieler aufgrund seines Levels verdient hat
    earned_titles = []
    if lvl >= 20: earned_titles.append("title_profi")
    if lvl >= 30: earned_titles.append("title_meister")
    if lvl >= 40: earned_titles.append("title_grossmeister")
    if lvl >= 50: earned_titles.append("title_legend")
    if lvl >= 65: earned_titles.append("title_mythos")
    if lvl >= 80: earned_titles.append("title_titan")
    if lvl >= 90: earned_titles.append("title_halbgott")
    if lvl >= 100: earned_titles.append("title_universum")

    if not earned_titles:
        return

    # Inventar auslesen
    inv = json.loads(user.inventory) if user.inventory else []
    owned_ids = [i if isinstance(i, str) else i.get('id') for i in inv]
    
    changed = False
    
    # Fehlende Titel lautlos direkt ins Inventar legen
    for title_id in earned_titles:
        if title_id not in owned_ids:
            inv.append({"id": title_id, "bought_at": datetime.utcnow().isoformat()})
            changed = True
            
    # Nur speichern, wenn es etwas Neues gab (spart Server-Leistung)
    if changed:
        user.inventory = json.dumps(inv)
        db.session.commit()

def get_user_metadata():
    all_users = UserSetting.query.all()
    meta = {}
    for u in all_users:
        titles = []
        
        if u.active_title:
            try:
                titles = json.loads(u.active_title) if u.active_title.startswith('[') else [u.active_title]
            except:
                titles = [u.active_title]
        
        titel_text = "".join([f"[{t}]" for t in titles if t])
        farbe = u.active_color if u.active_color else "white"
        display_n = u.display_name if u.display_name else u.username
        
        meta[u.username] = {"color": farbe, "title": titel_text, "display_name": display_n}
    return meta

def get_klassen_liste_fuer_user(username):
    user = UserSetting.query.filter_by(username=username).first()
    if not user or not user.klasse:
        return ["Till"]
        
    # --- FIX: Alte Klassennamen automatisch updaten ---
    such_klasse = user.klasse
    if such_klasse == "G8c":
        such_klasse = "Klasse G8c"
        user.klasse = "Klasse G8c"  # Updatet den alten Eintrag des Schülers
        db.session.commit()         # Speichert die Korrektur in der Datenbank
        
    students = AllowedStudent.query.filter_by(class_name=such_klasse).all()
    liste = [s.name for s in students]
    
    if "Till" not in liste: 
        liste.append("Till")
    return liste


# --- ROUTEN ---
@app.before_request
def update_last_seen():
    if 'username' in session:
        current_user = session['username']
        user = UserSetting.query.filter_by(username=current_user).first()
        if user:
            user.last_seen = datetime.utcnow()
            db.session.commit()
        last_active[current_user] = datetime.now()


@app.before_request
def check_if_banned():
    if request.endpoint in ['login', 'static']:
        return
    if 'username' in session:
        user = UserSetting.query.filter_by(username=session['username']).first()
        if user and user.banned_until:
            if user.banned_until > datetime.utcnow():
                session.pop('username', None)
                return f"""
                <div style='background:#222; color:white; font-family:sans-serif; text-align:center; padding-top:100px;'>
                    <h1 style='color:#ff2e63;'>🚫 DU WURDEST GEBANNT!</h1>
                    <p>Dein Zugang wurde gesperrt.</p>
                    <a href='/login' style='color:#00adb5;'>Zurück zum Login</a>
                </div>
                """, 403
            else:
                user.banned_until = None
                db.session.commit()




@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/impressum')
def impressum_page():
    return render_template('impressum.html')

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')


@app.route('/api/ping', methods=['POST'])
def ping_user():
    if 'username' in session:
        current_user = session['username']
        last_active[current_user] = datetime.now()
        
        data = request.get_json(silent=True) or {}
        activity = data.get('activity', 'Im Portal')
        is_afk = data.get('is_afk', False)
        is_bot = data.get('is_bot', False) 
        
        if is_bot:
            user_activities[current_user] = f"{activity} (BOT VERDACHT)"
        elif is_afk:
            user_activities[current_user] = f"{activity} (AFK)"
        else:
            user_activities[current_user] = activity
        
        if not is_afk and not is_bot:
            user = UserSetting.query.filter_by(username=current_user).first()
            if user:
                user.playtime_total = (user.playtime_total or 0) + 5
                user.xp = (user.xp or 0) + 2 
                if (user.playtime_total % 25) == 0: 
                    user.coins = (user.coins or 0) + 1

                check_rank_titles(user)
                check_playtime_auras(user)

                if activity.startswith("Spielt "):
                    game_name = activity.replace("Spielt ", "").lower()
                    score_entry = GameScore.query.filter_by(username=current_user).first()
                    if not score_entry:
                        score_entry = GameScore(username=current_user)
                        db.session.add(score_entry)
                    
                    if game_name == "geometry dash": score_entry.playtime_gd = (score_entry.playtime_gd or 0) + 5
                    elif game_name == "clicker": score_entry.playtime_clicker = (score_entry.playtime_clicker or 0) + 5
                    elif game_name == "flappy bird": score_entry.playtime_flappy = (score_entry.playtime_flappy or 0) + 5
                    elif game_name == "reaction": score_entry.playtime_reaction = (score_entry.playtime_reaction or 0) + 5
                    elif game_name == "snake": score_entry.playtime_snake = (score_entry.playtime_snake or 0) + 5
                    elif game_name == "crossy": score_entry.playtime_crossy = (score_entry.playtime_crossy or 0) + 5
                    elif game_name == "neon jump": score_entry.playtime_doodle = (score_entry.playtime_doodle or 0) + 5
                    elif game_name == "brickbreaker": score_entry.playtime_brickbreaker = (score_entry.playtime_brickbreaker or 0) + 5
                    elif game_name == "speedtyping": score_entry.playtime_speedtyping = (score_entry.playtime_speedtyping or 0) + 5
                    elif game_name == "slither": score_entry.playtime_slither = (score_entry.playtime_slither or 0) + 5
                    elif game_name == "tower stack": score_entry.playtime_tower = (score_entry.playtime_tower or 0) + 5 
                    elif game_name == "neon dino": score_entry.playtime_dino = (score_entry.playtime_dino or 0) + 5 
            
                db.session.commit()
        
        return {"status": "success"}
    return {"error": "Unauthorized"}, 401

# --- NEU: Automatische Auren-Vergabe durch Spielzeit ---
def check_playtime_auras(user):
    if not user or not user.playtime_total: return
    
    inv = json.loads(user.inventory) if user.inventory else []
    owned_ids = [i if isinstance(i, str) else i.get('id') for i in inv]
    changed = False
    
    for item_id, data in SHOP_ITEMS.items():
        if data.get("playtime_req") and user.playtime_total >= data["playtime_req"]:
            if item_id not in owned_ids:
                inv.append({"id": item_id, "bought_at": datetime.utcnow().isoformat()})
                changed = True
                
    if changed:
        user.inventory = json.dumps(inv)
        db.session.commit()

# --- NEU: Kisten öffnen API ---
@app.route('/api/shop/open-box', methods=['POST'])
def open_box():
    if 'username' not in session: return {"error": "401"}, 401
    item_id = request.json.get('item_id')
    u = UserSetting.query.filter_by(username=session['username']).first()
    inv = json.loads(u.inventory) if u.inventory else []
    
    # Kiste im Inventar suchen und entfernen
    box_index = next((i for i, item in enumerate(inv) if (item if isinstance(item, str) else item.get('id')) == item_id), -1)
    if box_index == -1 or SHOP_ITEMS[item_id]["type"] != "lootbox":
        return {"error": "Kiste nicht gefunden!"}, 400
        
    inv.pop(box_index)
    
    # Belohnungs-Logik
    rand = random.random()
    gewinn_text = ""
    if item_id == "box_common":
        if rand < 0.5: 
            gewinn = 150; u.coins = (u.coins or 0) + gewinn; gewinn_text = f"{gewinn} Coins! 🪙"
        elif rand < 0.9: 
            gewinn = 250; u.xp = (u.xp or 0) + gewinn; gewinn_text = f"{gewinn} XP! 🌟"
        else:
            gewinn_text = "Titel: Ninja! 🥷"
            if "title_ninja" not in [i if isinstance(i, str) else i.get('id') for i in inv]:
                inv.append({"id": "title_ninja", "bought_at": datetime.utcnow().isoformat()})
                
    elif item_id == "box_epic":
        if rand < 0.4:
            gewinn = 600; u.coins = (u.coins or 0) + gewinn; gewinn_text = f"MEGA: {gewinn} Coins! 💰"
        elif rand < 0.8:
            gewinn = 1000; u.xp = (u.xp or 0) + gewinn; gewinn_text = f"MEGA: {gewinn} XP! 🔥"
        else:
            gewinn_text = "Exklusiver Titel: Hacker! 💻"
            if "title_hacker" not in [i if isinstance(i, str) else i.get('id') for i in inv]:
                inv.append({"id": "title_hacker", "bought_at": datetime.utcnow().isoformat()})

    u.inventory = json.dumps(inv)
    check_rank_titles(u)
    db.session.commit()
    return {"status": "success", "message": f"Kiste geöffnet! Du erhältst: {gewinn_text}"}


@app.route('/api/dashboard-stats')
def dashboard_stats():
    if 'username' in session: 
        current_user = session['username']
        user = UserSetting.query.filter_by(username=current_user).first()
        global_chat_len = ChatMessage.query.filter_by(room=f"Klasse_{user.klasse}").count()

        # --- NEU: Wenn der User nicht existiert, Cookie löschen und abbrechen ---
        if not user:
            session.pop('username', None)
            return {"error": "Nicht autorisiert"}, 401
        
        private_chats_stats = {}
        for schueler in get_klassen_liste_fuer_user(current_user):
            if schueler != current_user:
                room_id = get_private_room_name(current_user, schueler)
                private_chats_stats[schueler] = ChatMessage.query.filter_by(room=room_id).count()
                
        aktive_grenze = datetime.now() - timedelta(seconds=15)
        online_users = [u for u, t in last_active.items() if t > aktive_grenze]
        
        return {
            "global_messages_count": global_chat_len,
            "private_messages_stats": private_chats_stats,
            "online_users": online_users,
            "user_activities": user_activities
        }
    return {"error": "Nicht autorisiert"}, 401


# --- SHOP & INVENTAR ROUTEN ---
@app.route('/api/shop/data')
def shop_data():
    if 'username' not in session: return {}, 401
    username = session['username']
    u = UserSetting.query.filter_by(username=username).first()
    if not u: return {}, 404
    
    inv = json.loads(u.inventory) if u.inventory else []
    admins_list = get_admins_list()
    is_admin_user = (username == "Till" or u.is_admin or username in admins_list)
    
    if is_admin_user:
        admin_items = ["title_admin", "title_crown", "color_purple"]
        owned_ids = [i if isinstance(i, str) else i.get('id') for i in inv]
        for ai in admin_items:
            if ai not in owned_ids:
                inv.append({"id": ai, "bought_at": datetime.utcnow().isoformat()})
        u.inventory = json.dumps(inv)
        db.session.commit()

    filtered_shop_items = {}
    for item_id, item_data in SHOP_ITEMS.items():
        if item_data.get("admin_only"):
            if is_admin_user:
                filtered_shop_items[item_id] = item_data
        else:
            filtered_shop_items[item_id] = item_data
            
    try:
        active_titles = json.loads(u.active_title) if u.active_title and u.active_title.startswith('[') else ([u.active_title] if u.active_title else [])
    except:
        active_titles = [u.active_title] if u.active_title else []

    return jsonify({
        "coins": u.coins or 0,
        "inventory": inv,
        "active_title": active_titles,
        "active_color": u.active_color,
        "shop_items": filtered_shop_items
    })

@app.route('/api/shop/buy', methods=['POST'])
def shop_buy():
    if 'username' not in session: return {"error": "401"}, 401
    item_id = request.json.get('item_id')
    if item_id not in SHOP_ITEMS: return {"error": "Item nicht gefunden"}, 400
    
    u = UserSetting.query.filter_by(username=session['username']).first()
    inv = json.loads(u.inventory) if u.inventory else []
    admins_list = get_admins_list()
    is_admin_user = (session['username'] == "Till" or u.is_admin or session['username'] in admins_list)

    if SHOP_ITEMS[item_id].get("admin_only") and not is_admin_user:
        return {"error": "Dieses Item ist exklusiv für Admins!"}, 403

    # --- NEU: Verhindern, dass jemand per direkter API-Anfrage Rang-Titel kauft ---
    if SHOP_ITEMS[item_id].get("rank_only"):
        return {"error": "Dieser Titel wird automatisch durch Level-Ups freigeschaltet und kann nicht gekauft werden!"}, 403
    
    owned_ids = [i if isinstance(i, str) else i.get('id') for i in inv]
    if item_id in owned_ids: return {"error": "Du besitzt dieses Item bereits!"}, 400
    
    price = SHOP_ITEMS[item_id]["price"]
    if (u.coins or 0) < price: return {"error": "Nicht genug Münzen!"}, 400
    
    u.coins -= price
    inv.append({
        "id": item_id,
        "bought_at": datetime.utcnow().isoformat()
    })
    u.inventory = json.dumps(inv)
    db.session.commit()
    return {"status": "success", "coins": u.coins}

@app.route('/api/shop/return', methods=['POST'])
def shop_return():
    if 'username' not in session: return {"error": "401"}, 401
    item_id = request.json.get('item_id')
    if item_id not in SHOP_ITEMS: return {"error": "Item nicht gefunden"}, 400
    
    u = UserSetting.query.filter_by(username=session['username']).first()
    inv = json.loads(u.inventory) if u.inventory else []
    
    target_item = None
    target_index = -1
    for idx, item in enumerate(inv):
        iid = item if isinstance(item, str) else item.get('id')
        if iid == item_id:
            target_item = item
            target_index = idx
            break
            
    if target_index == -1:
        return {"error": "Du besitzt dieses Item nicht!"}, 400
        
    if isinstance(target_item, str):
        return {"error": "Dieses Item kann nicht zurückgegeben werden."}, 400
        
    bought_at_str = target_item.get('bought_at')
    if not bought_at_str:
        return {"error": "Rückgabezeitraum abgelaufen."}, 400
        
    bought_at = datetime.fromisoformat(bought_at_str)
    if datetime.utcnow() - bought_at > timedelta(hours=24):
        return {"error": "Der Rückgabezeitraum von 24 Stunden ist abgelaufen!"}, 400
        
    price = SHOP_ITEMS[item_id]["price"]
    if price <= 0:
        return {"error": "Dieses Item kann nicht zurückgegeben werden."}, 400
        
    inv.pop(target_index)
    u.inventory = json.dumps(inv)
    u.coins = (u.coins or 0) + price
    
    item = SHOP_ITEMS[item_id]
    if item["type"] == "title":
        try:
            active_titles = json.loads(u.active_title) if u.active_title and u.active_title.startswith('[') else ([u.active_title] if u.active_title else [])
        except:
            active_titles = [u.active_title] if u.active_title else []
        if item["value"] in active_titles:
            active_titles.remove(item["value"])
            u.active_title = json.dumps(active_titles)
    elif item["type"] == "color":
        if u.active_color == item["value"]:
            u.active_color = None
            
    db.session.commit()
    return {"status": "success", "coins": u.coins}

@app.route('/api/shop/equip', methods=['POST'])
def shop_equip():
    if 'username' not in session: return {"error": "401"}, 401
    item_id = request.json.get('item_id')
    u = UserSetting.query.filter_by(username=session['username']).first()
    inv = json.loads(u.inventory) if u.inventory else []
    
    owned_ids = [i if isinstance(i, str) else i.get('id') for i in inv]
    if item_id not in owned_ids: return {"error": "Item nicht im Inventar!"}, 400
    
    item = SHOP_ITEMS[item_id]
    if item["type"] == "title":
        try:
            active_titles = json.loads(u.active_title) if u.active_title and u.active_title.startswith('[') else ([u.active_title] if u.active_title else [])
        except:
            active_titles = [u.active_title] if u.active_title else []
            
        if item["value"] in active_titles:
            active_titles.remove(item["value"])
        else:
            active_titles.append(item["value"])
        u.active_title = json.dumps(active_titles)
        
    elif item["type"] == "color":
        if u.active_color == item["value"]:
            u.active_color = None
        else:
            u.active_color = item["value"]
        
    db.session.commit()
    return {"status": "success"}

@app.route('/stats')
def global_stats():
    if 'username' not in session: return redirect(url_for('login'))
    
    me = session['username']
    meine_klasse = get_klassen_liste_fuer_user(me)
    
    all_users = UserSetting.query.filter(UserSetting.username.in_(meine_klasse)).all()
    all_scores = GameScore.query.filter(GameScore.username.in_(meine_klasse)).all()
    
    points = {u.username: 0 for u in all_users}
    
    def assign_points(game_attr, reverse=True, ignore_val=None):
        valid_scores = [s for s in all_scores if getattr(s, game_attr) is not None and getattr(s, game_attr) != ignore_val]
        valid_scores.sort(key=lambda x: getattr(x, game_attr), reverse=reverse)
        for i, s in enumerate(valid_scores[:10]): 
            points[s.username] += (10 - i)
            
    assign_points('geometry_dash', ignore_val=0)
    assign_points('clicker', ignore_val=0)
    assign_points('flappy', ignore_val=-1)
    assign_points('reaction', reverse=False, ignore_val=9999) 
    assign_points('snake', ignore_val=0)
    assign_points('crossy', ignore_val=0)
    assign_points('doodle', ignore_val=0)
    assign_points('brickbreaker', ignore_val=0)
    assign_points('speedtyping', ignore_val=0)
    assign_points('slither', ignore_val=0)
    assign_points('tower', ignore_val=0)
    assign_points('dino', ignore_val=0)
    
    efficiency_list = []
    for u in all_users:
        total_min = max(1, (u.playtime_total or 0) / 60.0)
        pts = points.get(u.username, 0)
        eff = round(pts / (total_min / 10), 2) 
        lvl, rank = get_level_info(u.xp)
        
        display_n = u.display_name if u.display_name else u.username
        
        efficiency_list.append({
            'name': display_n,
            'points': pts,
            'playtime_min': round((u.playtime_total or 0) / 60),
            'efficiency': eff,
            'level': lvl, 
            'rank': rank
        })
        
    efficiency_list.sort(key=lambda x: x['points'], reverse=True)
    scores_dict = {s.username: s for s in all_scores}
    meta = get_user_metadata()
    
    return render_template('stats.html', efficiency=efficiency_list, scores=scores_dict, meta=meta)

@app.route('/shop')
def shop_page():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    display_name = user.display_name if (user and user.display_name) else me
    return render_template('shop.html', name=display_name, user_coins=(user.coins if user else 0))

@app.route('/api/redeem-code', methods=['POST'])
def redeem_code():
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    me = session['username']
    code = request.json.get('code', '').strip().upper()
    
    if not code or code not in GEHEIME_CODES:
        return {"error": "Dieser Code ist ungültig oder existiert nicht!"}, 400
        
    already_used = RedeemedCode.query.filter_by(username=me, code=code).first()
    if already_used:
        return {"error": "Du hast diesen Code bereits eingelöst!"}, 400
        
    user = UserSetting.query.filter_by(username=me).first()
    if not user:
        return {"error": "Nutzer existiert nicht"}, 400

    belohnung = GEHEIME_CODES[code]
    msg = "Code akzeptiert!"

    if belohnung == "double_score":
        user.score_multiplier = 2  
        msg = "Code akzeptiert! Du hast ab sofort DOPPELTEN SCORE in den Spielen!"
    elif belohnung == "admin":
        user.is_admin = True
        msg = "Code akzeptiert! Du bist jetzt Admin!"
    else:
        try:
            teile = belohnung.split("_", 1)
            menge = int(teile[0])
            typ = teile[1]
            
            if typ == "coins":
                user.coins = (user.coins or 0) + menge
                msg = f"Code akzeptiert! +{menge} Münzen für den Shop! 🪙"
            elif typ == "xp":
                user.xp = (user.xp or 0) + menge
                msg = f"Code akzeptiert! +{menge} XP für dich! 🌟"
                check_rank_titles(user)
        except Exception:
            msg = "Code eingelöst!"
        
    db.session.add(RedeemedCode(username=me, code=code))
    db.session.commit()
    
    return {"status": "success", "message": msg}

@app.route('/api/daily-bonus', methods=['POST'])
def daily_bonus():
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    u = UserSetting.query.filter_by(username=session['username']).first()
    
    now = datetime.utcnow()
    if not u.last_daily_claim or (now - u.last_daily_claim).days >= 1:
        if u.last_daily_claim and (now - u.last_daily_claim).days > 2:
            u.login_streak = 1
        else:
            u.login_streak = (u.login_streak or 0) + 1
            
        belohnung = 10 + (u.login_streak * 5)
        if belohnung > 100: belohnung = 100 
        
        u.coins = (u.coins or 0) + belohnung
        u.last_daily_claim = now
        db.session.commit()
        return {"status": "success", "coins": belohnung, "streak": u.login_streak}
    
    return {"error": "Du hast deinen Bonus heute schon abgeholt! Komm morgen wieder."}, 400

@app.route('/daily')
def daily_page():
    if 'username' not in session: return redirect(url_for('login'))
    user = UserSetting.query.filter_by(username=session['username']).first()
    
    now = datetime.utcnow()
    can_claim = True
    
    if user.last_daily_claim and (now - user.last_daily_claim).days < 1:
        can_claim = False
        
    streak = user.login_streak or 0
    return render_template('daily_bonus.html', streak=streak, can_claim=can_claim, coins=(user.coins or 0))


@app.route('/api/milestones')
def class_milestones():
    if 'username' not in session: return {"error": "401"}, 401
    me = session['username']
    meine_klasse = get_klassen_liste_fuer_user(me)
    
    alle_user = UserSetting.query.filter(UserSetting.username.in_(meine_klasse)).all()
    gesamt_playtime = sum([(u.playtime_total or 0) for u in alle_user])
    gesamt_coins = sum([(u.coins or 0) for u in alle_user])
    
    # 1 Stunde = 3600 Punkte
    playtime_stunden = round(gesamt_playtime / 3600, 1)
    
    return jsonify({
        "playtime_hours": playtime_stunden,
        "playtime_goal": 2000, # Ziel: 2000 Stunden gemeinsam
        "total_coins": gesamt_coins,
        "coins_goal": 50000 # Ziel: 50.000 Coins gemeinsam
    })


@app.route('/gluecksrad')
def wheel_page():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    display_name = user.display_name if (user and user.display_name) else me
    return render_template('gluecksrad.html', name=display_name, coins=(user.coins if user else 0))

@app.route('/api/spin-wheel', methods=['POST'])
def spin_wheel():
    if 'username' not in session: return {"error": "401"}, 401
    u = UserSetting.query.filter_by(username=session['username']).first()
    
    einsatz = 15
    if (u.coins or 0) < einsatz: return {"error": f"Du brauchst {einsatz} Münzen zum Drehen!"}, 400
    
    u.coins -= einsatz
    
    rand = random.random()
    if rand < 0.60: 
        gewinn, text, segment = 0, "Niete! 😭", "niete"
    elif rand < 0.85: 
        gewinn, text, segment = 20, "20 Münzen! 🪙", "20coins"
    elif rand < 0.95: 
        gewinn, text, segment = 50, "50 Münzen! 💰", "50coins"
    elif rand < 0.99: 
        gewinn, text, segment = 100, "JACKPOT! 100 Münzen! 💎", "jackpot"
    else: 
        gewinn, text, segment = 0, "XP-Boost! +500 XP 🌟", "xp"
        u.xp = (u.xp or 0) + 500
        check_rank_titles(u)
        
    u.coins += gewinn
    db.session.commit()
    
    return {"status": "success", "text": text, "new_balance": u.coins, "segment": segment}

@app.route('/gluecksrad/premium')
def premium_wheel_page():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    display_name = user.display_name if (user and user.display_name) else me
    return render_template('gluecksrad_premium.html', name=display_name, coins=(user.coins if user else 0))

@app.route('/api/spin-wheel-premium', methods=['POST'])
def spin_wheel_premium():
    if 'username' not in session: return {"error": "401"}, 401
    u = UserSetting.query.filter_by(username=session['username']).first()
    
    einsatz = 30
    if (u.coins or 0) < einsatz: return {"error": f"Du brauchst {einsatz} Münzen zum Drehen!"}, 400
    
    u.coins -= einsatz
    
    rand = random.random()
    if rand < 0.65: 
        gewinn, text, segment = 0, "Niete! 💸", "niete"
    elif rand < 0.85: 
        gewinn, text, segment = 40, "40 Münzen! 🪙", "40coins"
    elif rand < 0.95: 
        gewinn, text, segment = 100, "100 Münzen! 💰", "100coins"
    elif rand < 0.99: 
        gewinn, text, segment = 250, "MEGA JACKPOT! 250 Münzen! 💎", "jackpot"
    else: 
        gewinn, text, segment = 0, "MEGA XP-Boost! +1000 XP 🔥", "xp"
        u.xp = (u.xp or 0) + 1000
        check_rank_titles(u)
        
    u.coins += gewinn
    db.session.commit()
    
    return {"status": "success", "text": text, "new_balance": u.coins, "segment": segment}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
        
    if SchoolClass.query.count() == 0:
        db.session.add(SchoolClass(name="Admin-Bereich"))
        db.session.add(SchoolClass(name="Klasse G8c"))
        db.session.commit()
        
    alle_klassen = SchoolClass.query.all()
        
    if request.method == 'POST':
        eingabe_klasse = request.form.get('klasse')
        eingabe_name = request.form.get('nutzername', '').strip()
        eingabe_pin = request.form.get('pin', '').strip()

        # --- NEU: Prüfen, ob der eingegebene Name ein geänderter Anzeigename (display_name) ist ---
        user_by_display = UserSetting.query.filter(db.func.lower(UserSetting.display_name) == eingabe_name.lower()).first()
        
        # Wenn wir einen passenden display_name finden, nehmen wir den dazugehörigen echten username
        if user_by_display:
            echter_username = user_by_display.username
        else:
            # Ansonsten gehen wir davon aus, dass der echte Name eingegeben wurde
            echter_username = eingabe_name

        db_such_klasse = eingabe_klasse
        if db_such_klasse.lower() == "g8c":
            db_such_klasse = "Klasse G8c"
        
        # Wir prüfen den ECHTEN Namen in der Erlaubt-Liste
        erlaubt = AllowedStudent.query.filter(
            db.func.lower(AllowedStudent.name) == echter_username.lower(),
            db.func.lower(AllowedStudent.class_name) == db_such_klasse.lower()
        ).first()
        is_till = (echter_username == "Till")
        
        if not erlaubt and not is_till:
            return render_template('login.html', klassen=alle_klassen, fehler=f'"{eingabe_name}" ist in der Klasse {eingabe_klasse} nicht eingetragen!', name_vorbefuellt=eingabe_name)
            
        user = UserSetting.query.filter_by(username=echter_username).first()
        
        if user and user.pin:
            if user.pin == eingabe_pin:
                session['username'] = echter_username  # Session läuft immer über den echten Namen
                session['klasse'] = eingabe_klasse
                last_active[echter_username] = datetime.now()
                user.klasse = eingabe_klasse
                check_rank_titles(user)
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', klassen=alle_klassen, fehler="Falsche PIN! 🤔", name_vorbefuellt=eingabe_name)
        else:
            if len(eingabe_pin) < 4:
                return render_template('login.html', klassen=alle_klassen, info="Erstelle bitte eine mindestens 4-stellige PIN!", name_vorbefuellt=eingabe_name)
            
            if not user:
                user = UserSetting(username=echter_username, display_name=echter_username, pin=eingabe_pin, is_admin=is_till, klasse=eingabe_klasse)
                db.session.add(user)
            else:
                user.pin = eingabe_pin
                user.klasse = eingabe_klasse
                if not user.display_name:
                    user.display_name = echter_username
            
            check_rank_titles(user)
            db.session.commit()
            
            session['username'] = echter_username
            session['klasse'] = eingabe_klasse
            last_active[echter_username] = datetime.now()
            return redirect(url_for('dashboard'))
            
    return render_template('login.html', klassen=alle_klassen)

@app.route('/welcome')
def dashboard():
    if 'username' not in session: 
        return redirect(url_for('login'))
    
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    
    check_rank_titles(user)

    display_name = user.display_name if (user and user.display_name) else me
    
    admin_msg = AdminMessage.query.filter((AdminMessage.target == 'alle') | (AdminMessage.target == me)).order_by(AdminMessage.id.desc()).first()
    
    zeige_spezial_nachricht = False
    spezial_titel = ""
    spezial_text = ""
    spezial_nachricht_id = ""
    
    if admin_msg:
        zeige_spezial_nachricht = True
        spezial_titel = admin_msg.title
        spezial_text = admin_msg.message
        spezial_nachricht_id = f"admin_msg_{admin_msg.id}"
    
    aktive_matches = []
    
    ttt_games = TicTacToeGame.query.filter(((TicTacToeGame.ersteller == me) | (TicTacToeGame.gegner == me)) & (TicTacToeGame.status == "aktiv")).all()
    for g in ttt_games:
        gegner_name = g.gegner if g.ersteller == me else g.ersteller
        gegner_u = UserSetting.query.filter_by(username=gegner_name).first()
        gegner_display = gegner_u.display_name if (gegner_u and gegner_u.display_name) else gegner_name
        aktive_matches.append({"id": g.game_id, "von": f"Tic-Tac-Toe vs. {gegner_display}", "is_active": True, "typ": "tictactoe"})

    tank_games = TankGame.query.filter(((TankGame.ersteller == me) | (TankGame.gegner == me)) & (TankGame.status == "aktiv")).all()
    for g in tank_games:
        gegner_name = g.gegner if g.ersteller == me else g.gegner
        gegner_u = UserSetting.query.filter_by(username=gegner_name).first()
        gegner_display = gegner_u.display_name if (gegner_u and gegner_u.display_name) else gegner_name
        aktive_matches.append({"id": g.game_id, "von": f"Tank Royale vs. {gegner_display}", "is_active": True, "typ": "tankroyale"})

    is_admin = True if (me == "Till" or (user and user.is_admin)) else False
    
    lvl, rank = get_level_info(user.xp if user else 0)
    
    meta = get_user_metadata()
    chpartner = []
    for s in sorted([s for s in get_klassen_liste_fuer_user(session['username']) if s != session['username']]):
        d_name = meta.get(s, {}).get('display_name', s)
        chpartner.append({'username': s, 'display_name': d_name})
    
    return render_template('dashboard.html', 
                           name=display_name, 
                           einladungen=aktive_matches, 
                           is_admin=is_admin,
                           user_level=lvl, 
                           user_rank=rank, 
                           user_xp=(user.xp if user else 0), 
                           user_coins=(user.coins if user else 0),
                           partner=chpartner,
                           zeige_spezial_nachricht=zeige_spezial_nachricht,
                           spezial_nachricht_id=spezial_nachricht_id,
                           spezial_titel=spezial_titel,
                           spezial_text=spezial_text)

@app.route('/api/change-pin', methods=['POST'])
def change_pin():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data = request.get_json(silent=True) or {}
    new_pin = str(data.get('new_pin', '')).strip()
    confirm_pin = str(data.get('confirm_pin', '')).strip()
    
    if not new_pin or len(new_pin) < 4:
        return {"error": "Der neue PIN muss mindestens 4 Zeichen lang sein!"}, 400
    if new_pin != confirm_pin:
        return {"error": "Die beiden PINs stimmen nicht überein!"}, 400
        
    current_user = session['username']
    user = UserSetting.query.filter_by(username=current_user).first()
    if user:
        user.pin = new_pin
        db.session.commit()
        return {"status": "success"}
    return {"error": "Nutzer nicht gefunden"}, 404

@app.route('/api/change-name', methods=['POST'])
def change_name():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    data = request.get_json(silent=True) or {}
    new_name = str(data.get('new_name', '')).strip()
    
    if not new_name or len(new_name) < 2:
        return {"error": "Der Name muss mindestens 2 Zeichen lang sein!"}, 400
    if len(new_name) > 30:
        return {"error": "Der Name ist zu lang (max. 30 Zeichen)."}, 400
        
    current_user = session['username']
    
    if new_name in get_klassen_liste_fuer_user(current_user) and new_name != current_user:
        user = UserSetting.query.filter_by(username=current_user).first()
        if user:
            user.banned_until = datetime.utcnow() + timedelta(days=1)
            db.session.commit()
        session.pop('username', None)
        return {"error": "Identitätsfälschung erkannt! Du hast versucht, dich als eine andere Person auszugeben und wurdest für 24 Stunden gebannt!"}, 403

    existing_display = UserSetting.query.filter(UserSetting.display_name == new_name, UserSetting.username != current_user).first()
    if existing_display:
        return {"error": "Dieser Name wird bereits von jemand anderem verwendet!"}, 400

    user = UserSetting.query.filter_by(username=current_user).first()
    if user:
        user.display_name = new_name
        db.session.commit()
        return {"status": "success", "new_name": new_name}
    return {"error": "Nutzer nicht gefunden"}, 404


@app.route('/admin')
def admin_panel():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "Zugriff verweigert!", 403
        
    all_users = UserSetting.query.all()
    pins_dict = {u.username: u.pin for u in all_users if u.pin}
    admins_list = get_admins_list()
    
    echte_klassen = SchoolClass.query.all()
    echte_schueler = AllowedStudent.query.all()
    
    banned_users = {}
    for u in all_users:
        if u.banned_until and u.banned_until > datetime.utcnow():
            if u.banned_until.year > 2090: banned_users[u.username] = "Permanent (Für immer)"
            else: banned_users[u.username] = u.banned_until.strftime("%d.%m.%Y - %H:%M Uhr")

    
    # --- NEU: Feedback aus der Datenbank laden ---
    ungelesenes_feedback = Feedback.query.filter_by(is_read=False).all()
    
    # --- NEU: feedback_liste=ungelesenes_feedback am Ende hinzufügen ---
    return render_template('admin.html', 
                           pins=pins_dict, 
                           admins=admins_list, 
                           klassen_liste=[s.name for s in AllowedStudent.query.all()], 
                           banned_users=banned_users, 
                           meta=get_user_metadata(), 
                           echte_klassen=echte_klassen, 
                           echte_schueler=echte_schueler,
                           feedback_liste=ungelesenes_feedback)

@app.route('/admin/make-admin', methods=['POST'])
def make_admin():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    neuer_admin = request.form.get('schueler')
    if True:
        target_user = UserSetting.query.filter_by(username=neuer_admin).first()
        if not target_user:
            target_user = UserSetting(username=neuer_admin, display_name=neuer_admin, is_admin=True)
            db.session.add(target_user)
        else: target_user.is_admin = True
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
    
    # Löscht den alten "global" Chat UND alle neuen Klassen-Chats (die mit "Klasse_" anfangen)
    ChatMessage.query.filter(ChatMessage.room.like('Klasse_%')).delete()
    ChatMessage.query.filter_by(room='global').delete()
    
    # Systemnachricht in alle existierenden Klassen schicken
    alle_klassen = SchoolClass.query.all()
    for klasse in alle_klassen:
        system_msg = ChatMessage(room=f"Klasse_{klasse.name}", sender='System', text='Der Chat wurde vom Admin aufgeräumt! 🧹')
        db.session.add(system_msg)
        
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    schueler = request.form.get('schueler')
    dauer = request.form.get('dauer')
    if schueler and schueler != "Till":
        target_user = UserSetting.query.filter_by(username=schueler).first()
        if not target_user:
            target_user = UserSetting(username=schueler, display_name=schueler)
            db.session.add(target_user)
        now = datetime.utcnow()
        if dauer == "1h": target_user.banned_until = now + timedelta(hours=1)
        elif dauer == "1d": target_user.banned_until = now + timedelta(days=1)
        elif dauer == "1w": target_user.banned_until = now + timedelta(weeks=1)
        elif dauer == "perm": target_user.banned_until = now + timedelta(days=36500)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/unban/<schueler>', methods=['POST'])
def admin_unban(schueler):
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    target_user = UserSetting.query.filter_by(username=schueler).first()
    if target_user:
        target_user.banned_until = None
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/send-message', methods=['POST'])
def send_admin_message():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403
    target = request.form.get('target', 'alle')
    title = request.form.get('title', 'Systemnachricht')
    message = request.form.get('message', '').strip()
    if message:
        AdminMessage.query.filter_by(target=target).delete()
        new_msg = AdminMessage(sender=me, target=target, title=title, message=message)
        db.session.add(new_msg)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add-class', methods=['POST'])
def add_class():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403

    class_name = request.form.get('class_name').strip()
    if class_name:
        if not SchoolClass.query.filter_by(name=class_name).first():
            db.session.add(SchoolClass(name=class_name))
            db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add-student', methods=['POST'])
def add_student():
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403

    student_name = request.form.get('student_name').strip()
    class_name = request.form.get('class_name').strip()
    
    if student_name and class_name:
        if not AllowedStudent.query.filter_by(name=student_name, class_name=class_name).first():
            db.session.add(AllowedStudent(name=student_name, class_name=class_name))
            db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove-class/<class_name>', methods=['POST'])
def remove_class(class_name):
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403

    SchoolClass.query.filter_by(name=class_name).delete()
    AllowedStudent.query.filter_by(class_name=class_name).delete()
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove-student/<int:student_id>', methods=['POST'])
def remove_student_from_class(student_id):
    if 'username' not in session: return "403", 403
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return "403", 403

    AllowedStudent.query.filter_by(id=student_id).delete()
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
        
    data = request.get_json(silent=True) or {}
    msg = data.get('message', '').strip()
    
    if not msg: return {"error": "Leere Nachricht"}, 400
    new_fb = Feedback(sender=session['username'], message=msg, is_read=False)
    db.session.add(new_fb)
    db.session.commit()
    return {"status": "success"}

@app.route('/api/admin/feedback', methods=['GET'])
def get_admin_feedback():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    me = session['username']
    user = UserSetting.query.filter_by(username=me).first()
    if not (me == "Till" or (user and user.is_admin)): return {"error": "Keine Rechte"}, 403
    unread = Feedback.query.filter_by(is_read=False).all()
    result = [{"id": f.id, "sender": f.sender, "message": f.message} for f in unread]
    return jsonify(result)

@app.route('/api/admin/feedback/read/<int:fb_id>', methods=['POST'])
def mark_feedback_read(fb_id):
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    fb = Feedback.query.get(fb_id)
    if fb:
        fb.is_read = True
        db.session.commit()
    return {"status": "success"}

@app.route('/chat')
@app.route('/chat/<room>')
def chat(room="global"):
    room = urllib.parse.unquote(room) # <-- FIX: Wandelt %20 in ein echtes Leerzeichen um
    if 'username' not in session: return redirect(url_for('login'))
    zwei_minuten_ago = datetime.utcnow() - timedelta(minutes=2)
    online_users = UserSetting.query.filter(UserSetting.last_seen >= zwei_minuten_ago).all()
    online_names = [u.display_name if u.display_name else u.username for u in online_users]

    current_user = session['username']
    meta = get_user_metadata()
    chpartner = []
    for schueler in sorted([s for s in get_klassen_liste_fuer_user(session['username']) if s != current_user]):
        d_name = meta.get(schueler, {}).get('display_name', schueler)
        chpartner.append({'username': schueler, 'display_name': d_name})
    
    admins = get_admins_list()
    return render_template('chat.html', room=room, partner=chpartner, admins=admins, online_liste=online_names)

@app.route('/chat/<room>/send', methods=['POST'])
def send_message(room):
    room = urllib.parse.unquote(room) # <-- FIX
    if 'username' not in session: return {"error": "Login erforderlich"}, 401
    nachricht_text = request.form.get('message', '').strip()
    if not nachricht_text: return {"status": "empty"}, 400
    current_user = session['username']
    user = UserSetting.query.filter_by(username=current_user).first()

    if not user:
        session.pop('username', None)
        return redirect(url_for('login'))
    
    if room == "global": actual_room = f"Klasse_{user.klasse}"
    else: actual_room = get_private_room_name(current_user, room)
    
    new_msg = ChatMessage(room=actual_room, sender=current_user, text=nachricht_text)
    db.session.add(new_msg)
    db.session.commit()
    return {"status": "success"}

@app.route('/api/chat-messages/<room>')
def api_chat_messages(room):
    room = urllib.parse.unquote(room) # <-- FIX
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    user = UserSetting.query.filter_by(username=current_user).first()

    if not user:
        session.pop('username', None)
        return {"error": "Nicht autorisiert"}, 401
    
    if room == "global": 
        actual_room = f"Klasse_{user.klasse}"
        partner = None
    else:
        partner = room
        actual_room = get_private_room_name(current_user, partner)
        
    db_messages = ChatMessage.query.filter_by(room=actual_room).order_by(ChatMessage.id.asc()).all()[-150:]
    
    all_users = UserSetting.query.all()
    meta = {}
    for u in all_users:
        lvl, _ = get_level_info(u.xp)
        display_n = u.display_name if u.display_name else u.username
        meta[u.username] = {'lvl': lvl, 'title': u.active_title, 'color': u.active_color, 'display_name': display_n}

    partner_seen_count = 9999
    if room != "global":
        total_msg_count = ChatMessage.query.filter_by(room=actual_room).count()
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
        u_meta = meta.get(m.sender, {'lvl': 1, 'title': None, 'color': None, 'display_name': m.sender})
        nachrichten.append({
            "name": u_meta['display_name'], 
            "text": m.text, 
            "gelesen": (index < partner_seen_count) if room != "global" else True,
            "level": u_meta['lvl'], 
            "title": u_meta['title'], 
            "color": u_meta['color']
        })
    return jsonify(nachrichten)

@app.route('/chat/<room>/delete/<int:msg_index>', methods=['POST'])
def delete_message(room, msg_index):
    room = urllib.parse.unquote(room) # <-- FIX
    if 'username' not in session: return redirect(url_for('login'))
    current_user = session['username']
    user = UserSetting.query.filter_by(username=current_user).first()
    admins = get_admins_list()
    
    if room == "global": actual_room = f"Klasse_{user.klasse}"
    else: actual_room = get_private_room_name(current_user, room)
    
    db_messages = ChatMessage.query.filter_by(room=actual_room).order_by(ChatMessage.id.asc()).all()
    sliced_messages = db_messages[-150:]
    
    if 0 <= msg_index < len(sliced_messages):
        target_msg = sliced_messages[msg_index]
        if target_msg.sender == current_user or current_user in admins:
            db.session.delete(target_msg)
            db.session.commit()
    return redirect(url_for('chat', room=room))

@app.route('/slither')
def slither_menu():
    if 'username' not in session: return redirect(url_for('login'))
    
    now = time.time()
    active_players = []
    for p, data in list(SLITHER_STATE["players"].items()):
        if now - data.get("last_seen", 0) > 5:
            del SLITHER_STATE["players"][p]
        else:
            active_players.append(p)
            
    return render_template('slither_menu.html', active_players=active_players)

@app.route('/slither/play')
def slither_play():
    if 'username' not in session: return redirect(url_for('login'))
    user = UserSetting.query.filter_by(username=session['username']).first()
    display_name = user.display_name if (user and user.display_name) else session['username']
    return render_template('slither_game.html', me=display_name)

@app.route('/api/slither/sync', methods=['POST'])
def slither_sync():
    if 'username' not in session: return {"error": "401"}, 401
    me = session['username']
    data = request.json or {}
    
    is_dead = data.get("is_dead", False)
    if is_dead:
        body = data.get("body", [])
        score = data.get("score", 0)
        color = data.get("color", "#fff")
        
        for segment in body[::2]:
            fid = str(uuid.uuid4())[:8]
            SLITHER_STATE["food"][fid] = {'x': segment[0], 'y': segment[1], 'c': color, 'v': 5}
            
        if me in SLITHER_STATE["players"]:
            del SLITHER_STATE["players"][me]
            
        multiplier = get_user_multiplier(me)
        final_score = int(score) * multiplier
        user_score = GameScore.query.filter_by(username=me).first()
        if not user_score:
            db.session.add(GameScore(username=me, slither=final_score))
        else:
            current_best = getattr(user_score, 'slither', 0)
            if current_best is None: current_best = 0
            if final_score > current_best: user_score.slither = final_score
        db.session.commit()
            
        return {"status": "dead"}

    eaten = data.get("eaten", [])
    for fid in eaten:
        if fid in SLITHER_STATE["food"]:
            del SLITHER_STATE["food"][fid]
            spawn_food(1) 

    SLITHER_STATE["players"][me] = {
        "body": data.get("body", []),
        "color": data.get("color", "#00adb5"),
        "score": data.get("score", 0),
        "last_seen": time.time()
    }
    
    for bot_id, bot in SLITHER_STATE["bots"].items():
        if not bot["body"]: continue
        head = bot["body"][0]
        bot["x"] = head[0]
        bot["y"] = head[1]
        
        bot["angle"] += random.uniform(-0.2, 0.2)
        speed = 5
        new_x = bot["x"] + math.cos(bot["angle"]) * speed
        new_y = bot["y"] + math.sin(bot["angle"]) * speed
        
        bot_radius = 10 + (bot["score"] / 20)
        bot_died = False
        
        for p_name, p_data in SLITHER_STATE["players"].items():
            if not p_data.get("body"): continue
            enemy_radius = 10 + (p_data.get("score", 0) / 20)
            for segment in p_data["body"]:
                dist = math.hypot(new_x - segment[0], new_y - segment[1])
                if dist < (bot_radius + enemy_radius) * 0.7:
                    bot_died = True
                    break
            if bot_died: break
            
        if not bot_died:
            for other_bot_id, other_bot in SLITHER_STATE["bots"].items():
                if other_bot_id == bot_id or not other_bot.get("body"): continue
                enemy_radius = 10 + (other_bot.get("score", 0) / 20)
                for segment in other_bot["body"]:
                    dist = math.hypot(new_x - segment[0], new_y - segment[1])
                    if dist < (bot_radius + enemy_radius) * 0.7:
                        bot_died = True
                        break
                if bot_died: break

        if bot_died or new_x < 0 or new_x > SLITHER_STATE["map_size"] or new_y < 0 or new_y > SLITHER_STATE["map_size"]:
            for segment in bot["body"][::2]:
                fid = str(uuid.uuid4())[:8]
                SLITHER_STATE["food"][fid] = {'x': segment[0], 'y': segment[1], 'c': bot["color"], 'v': 3}
            
            SLITHER_STATE["bots"][bot_id] = {
                "body": [[random.randint(1000, 2000), random.randint(1000, 2000)]],
                "color": random.choice(COLORS),
                "score": 50,
                "angle": random.uniform(0, math.pi * 2),
                "x": 0, "y": 0
            }
            continue
        
        bot["body"].insert(0, [new_x, new_y])
        if len(bot["body"]) > (bot["score"] // 10) + 5:
            bot["body"].pop()
            
        if random.random() < 0.02: bot["score"] += 1

    all_entities = []
    for p, d in SLITHER_STATE["players"].items(): all_entities.append((p, d["score"]))
    for b, d in SLITHER_STATE["bots"].items(): all_entities.append((b, d["score"]))
    leaderboard = sorted(all_entities, key=lambda x: x[1], reverse=True)[:5]

    return {
        "players": {p: d for p, d in SLITHER_STATE["players"].items() if p != me},
        "bots": SLITHER_STATE["bots"],
        "food": SLITHER_STATE["food"],
        "leaderboard": leaderboard
    }

# --- GAMES & LEADERBOARDS ---
@app.route('/games')
def games_menu():
    if 'username' not in session: return redirect(url_for('login'))
    me = session['username']
    ttt_invites = TicTacToeGame.query.filter_by(gegner=me, status='eingeladen').all()
    aktive_einladungen = [{"id": i.game_id, "von": i.ersteller, "typ": "tictactoe"} for i in ttt_invites]
    tank_invites = TankGame.query.filter_by(gegner=me, status='eingeladen').all()
    for i in tank_invites: aktive_einladungen.append({"id": i.game_id, "von": i.ersteller, "typ": "tankroyale"})
    return render_template('games.html', einladungen=aktive_einladungen)

@app.route('/geometry-dash')
def game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.geometry_dash for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('geometry_dash.html', leaderboard=leaderboard, meta=meta)
    
@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, geometry_dash=score))
    else:
        current_best = user_score.geometry_dash if user_score.geometry_dash is not None else 0
        if score > current_best: user_score.geometry_dash = score
    db.session.commit()
    return {"status": "success"}

@app.route('/clicker')
def clicker_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.clicker for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('clicker.html', leaderboard=leaderboard, meta=meta)
    
@app.route('/api/submit-clicker', methods=['POST'])
def submit_clicker():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, clicker=score))
    else:
        current_best = user_score.clicker if user_score.clicker is not None else 0
        if score > current_best: user_score.clicker = score
    db.session.commit()
    return {"status": "success"}

@app.route('/flappy')
def flappy_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.flappy for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('flappy.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-flappy', methods=['POST'])
def submit_flappy():
    if 'username' not in session: return {"error": "401"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    val = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, flappy=val))
    else:
        current_best = user_score.flappy if user_score.flappy is not None else -1
        if val > current_best: user_score.flappy = val
    db.session.commit()
    return {"status": "ok"}

@app.route('/reaction')
def reaction_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: s.reaction for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('reaction.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-reaction', methods=['POST'])
def submit_reaction():
    if 'username' not in session: return {"error": "401"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    val = int(int(request.json.get('score', 9999)) / multiplier)
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, reaction=val))
    else:
        current_best = user_score.reaction if user_score.reaction is not None else 9999
        if val < current_best: user_score.reaction = val
    db.session.commit()
    return {"status": "ok"}

@app.route('/snake')
def snake_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (s.snake if s.snake is not None else 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('snake.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-snake', methods=['POST'])
def submit_snake():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, snake=score))
    else:
        current_best = user_score.snake if user_score.snake is not None else 0
        if score > current_best: user_score.snake = score
    db.session.commit()
    return {"status": "success"}

@app.route('/crossy')
def crossy_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (s.crossy if s.crossy is not None else 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('crossy.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-crossy', methods=['POST'])
def submit_crossy():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, crossy=score))
    else:
        current_best = user_score.crossy if user_score.crossy is not None else 0
        if score > current_best: user_score.crossy = score
    db.session.commit()
    return {"status": "success"}

@app.route('/doodle')
def doodle_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (s.doodle if s.doodle is not None else 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('doodle.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-doodle', methods=['POST'])
def submit_doodle():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, doodle=score))
    else:
        current_best = user_score.doodle if user_score.doodle is not None else 0
        if score > current_best: user_score.doodle = score
    db.session.commit()
    return {"status": "success"}

@app.route('/brickbreaker')
def brickbreaker_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (s.brickbreaker if hasattr(s, 'brickbreaker') and s.brickbreaker is not None else 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('brickbreaker.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-brickbreaker', methods=['POST'])
def submit_brickbreaker():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, brickbreaker=score))
    else:
        current_best = getattr(user_score, 'brickbreaker', 0)
        if current_best is None: current_best = 0
        if score > current_best: user_score.brickbreaker = score
    db.session.commit()
    return {"status": "success"}

@app.route('/speedtyping')
def speedtyping_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (getattr(s, 'speedtyping', 0) or 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('speedtyping.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-speedtyping', methods=['POST'])
def submit_speedtyping():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: db.session.add(GameScore(username=current_user, speedtyping=score))
    else:
        current_best = getattr(user_score, 'speedtyping', 0)
        if current_best is None: current_best = 0
        if score > current_best: user_score.speedtyping = score
    db.session.commit()
    return {"status": "success"}

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/tictactoe')
def tictactoe_menu():
    if 'username' not in session: return redirect(url_for('login'))
    gegner_liste = sorted([s for s in get_klassen_liste_fuer_user(session['username']) if s != session['username']])
    return render_template('tictactoe_menu.html', gegner_liste=gegner_liste)

@app.route('/tictactoe/invite', methods=['POST'])
def tictactoe_invite():
    if 'username' not in session: return redirect(url_for('login'))
    gegner = request.form.get('gegner')
    me = session['username']
    game_id = get_ttt_id(me, gegner)
    existing = TicTacToeGame.query.filter_by(game_id=game_id).first()
    if existing: db.session.delete(existing)
    new_game = TicTacToeGame(game_id=game_id, ersteller=me, gegner=gegner, board=", , , , , , , , ", turn=me, status="eingeladen")
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
        return jsonify({"ersteller": g.ersteller, "gegner": g.gegner, "board": cleaned_board, "turn": g.turn, "status": g.status})
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

@app.route('/tankroyale')
def tankroyale_menu():
    if 'username' not in session: return redirect(url_for('login'))
    gegner_liste = sorted([s for s in get_klassen_liste_fuer_user(session['username']) if s != session['username']])
    return render_template('tank_royale_menu.html', gegner_liste=gegner_liste, meta=get_user_metadata())

@app.route('/tankroyale/invite', methods=['POST'])
def tankroyale_invite():
    if 'username' not in session: return redirect(url_for('login'))
    gegner = request.form.get('gegner')
    bot_difficulty = request.form.get('bot_difficulty', 'medium') 
    me = session['username']
    game_id = f"{min(me, gegner)}_tank_{max(me, gegner)}"
    existing = TankGame.query.filter_by(game_id=game_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit() 
    terrain_points = []
    for x in range(901):
        y = 400 + math.sin(x * 0.008) * 40 + math.cos(x * 0.02) * 10
        terrain_points.append(round(y, 2))
    terrain_json = json.dumps(terrain_points)
    new_game = TankGame(game_id=game_id, ersteller=me, gegner=gegner, state="100,100,80,620,100,100,3,2,3,2,-1,-1,0", turn=me, status="eingeladen", terrain=terrain_json)
    db.session.add(new_game)
    db.session.commit()
    return redirect(url_for('tankroyale_match', game_id=game_id, diff=bot_difficulty))

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
    diff = request.args.get('diff', 'medium')
    game = TankGame.query.filter_by(game_id=game_id).first()
    gegner_name = "Computer-Bot 🤖"
    if game:
        me = session['username']
        raw_gegner = game.gegner if game.ersteller == me else game.ersteller
        gegner_u = UserSetting.query.filter_by(username=raw_gegner).first()
        gegner_name = gegner_u.display_name if (gegner_u and gegner_u.display_name) else raw_gegner
    return render_template('tank_royale_match.html', gameId=game_id, me=session['username'], gegner=gegner_name, bot_difficulty=diff, meta=get_user_metadata())

@app.route('/api/tankroyale/status/<game_id>')
def tank_status(game_id):
    g = TankGame.query.filter_by(game_id=game_id).first()
    if not g: return {"status": "not_found"}, 404
    state_str = g.state or ""
    raw_parts = state_str.split(',') if state_str else []
    if len(raw_parts) < 13:
        default_parts = ["100", "100", "80", "620", "100", "100", "3", "2", "3", "2", "-1", "-1", "0"]
        for i in range(len(raw_parts)):
            if raw_parts[i] and raw_parts[i] != "NaN": default_parts[i] = raw_parts[i]
        raw_parts = default_parts
        g.state = ",".join(raw_parts)
        db.session.commit()
    def safe_int(val, default=0):
        try: return int(float(val))
        except (ValueError, TypeError): return default
    terrain_data = json.loads(g.terrain) if g.terrain else []
    return {
        "status": g.status or "aktiv",
        "turn": g.turn,
        "ersteller": g.ersteller,
        "gegner": g.gegner,
        "p1_hp": safe_int(raw_parts[0], 100),
        "p2_hp": safe_int(raw_parts[1], 100),
        "p1_x": safe_int(raw_parts[2], 80),
        "p2_x": safe_int(raw_parts[3], 620),
        "raw_state": g.state,
        "terrain": terrain_data
    }
    
@app.route('/api/tankroyale/shoot/<game_id>', methods=['POST'])
def tank_shoot(game_id):
    if 'username' not in session: return {"error": "Nicht eingeloggt"}, 401
    me = session['username']
    data = request.json or {}
    angle = float(data.get('angle', 0))
    power = float(data.get('power', 0))
    hit = data.get('hit', 'none')
    waffentyp = str(data.get('waffenTyp', 'standard')).lower().strip()
    g = TankGame.query.filter_by(game_id=game_id).first()
    if g and g.status == "aktiv" and g.turn == me:
        if "updated_terrain" in data and data["updated_terrain"]:
            g.terrain = json.dumps(data["updated_terrain"])
        raw_parts = g.state.split(',') if g.state else []
        def safe_float_convert(val, default=0):
            try: return int(float(val))
            except (ValueError, TypeError): return default
        if len(raw_parts) < 13: st = [100, 100, int(g.p1_x or 80), int(g.p2_x or 620), 100, 100, 3, 2, 3, 2, -1, -1, 0]
        else: st = [safe_float_convert(x) for x in raw_parts]
        
        if data.get('new_p1_x') is not None: st[2] = safe_float_convert(data.get('new_p1_x'))
        if data.get('new_p2_x') is not None: st[3] = safe_float_convert(data.get('new_p2_x'))
        
        if me == g.ersteller:
            if data.get('new_p1_fuel') is not None: st[4] = safe_float_convert(data.get('new_p1_fuel'))
        else:
            if data.get('new_p2_fuel') is not None: st[5] = safe_float_convert(data.get('new_p2_fuel'))

        if hit == "crate_collected":
            if me == g.ersteller:
                st[0] = min(100, st[0] + 25) 
                st[4] = 100  
                st[6] += 1   
                st[7] += 1   
            else:
                st[1] = min(100, st[1] + 25) 
                st[5] = 100  
                st[8] += 1
                st[9] += 1
            st[12] = 0        
        else:
            if me == g.ersteller:
                if waffentyp == "berta": st[6] = max(0, st[6] - 1)
                elif waffentyp == "triple": st[7] = max(0, st[7] - 1)
            else:
                if waffentyp == "berta": st[8] = max(0, st[8] - 1)
                elif waffentyp == "triple": st[9] = max(0, st[9] - 1)
            schaden = 20
            if waffentyp == "berta": schaden = 45
            elif waffentyp == "triple": schaden = 18
            if hit == "p1": st[0] = max(0, st[0] - schaden)
            elif hit == "p2": st[1] = max(0, st[1] - schaden)

        if st[12] == 0 and random.random() < 0.35:
            st[10] = random.randint(150, 750)
            st[11] = 0
            st[12] = 1

        g.p1_hp, g.p2_hp = st[0], st[1]
        g.p1_x, g.p2_x = st[2], st[3]
        g.state = ",".join(str(x) for x in st)
        g.last_shot = f"{angle},{power}"
        
        if st[0] <= 0: g.status = f"gewonnen_{g.gegner}"
        elif st[1] <= 0: g.status = f"gewonnen_{g.ersteller}"
        else: g.turn = g.gegner if me == g.ersteller else g.ersteller
            
        db.session.commit()
        return {"status": "success"}
    return {"status": "invalid_move"}, 400

@app.route('/tankroyale/delete-match/<game_id>', methods=['POST'])
def tankroyale_delete_match(game_id):
    if 'username' not in session: return redirect(url_for('login'))
    match = TankGame.query.filter_by(game_id=game_id).first()
    if match:
        db.session.delete(match)
        db.session.commit()
    return redirect(url_for('dashboard'))

# Tower Stack
@app.route('/tower-stack')
def tower_stack_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (getattr(s, 'tower', 0) or 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('tower_stack.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-tower', methods=['POST'])
def submit_tower():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: 
        db.session.add(GameScore(username=current_user, tower=score))
    else:
        current_best = getattr(user_score, 'tower', 0)
        if current_best is None: current_best = 0
        if score > current_best: 
            user_score.tower = score
    db.session.commit()
    return {"status": "success"}

# Dino Runner
@app.route('/games/dino')
def dino_game():
    if 'username' not in session: return redirect(url_for('login'))
    all_scores = GameScore.query.all()
    scores_dict = {s.username: (getattr(s, 'dino', 0) or 0) for s in all_scores}
    leaderboard = sorted([(s, scores_dict.get(s, 0)) for s in get_klassen_liste_fuer_user(session['username'])], key=lambda x: x[1], reverse=True)
    meta = get_user_metadata()
    return render_template('dino.html', leaderboard=leaderboard, meta=meta)

@app.route('/api/submit-dino', methods=['POST'])
def submit_dino():
    if 'username' not in session: return {"error": "Nicht autorisiert"}, 401
    current_user = session['username']
    multiplier = get_user_multiplier(current_user)
    score = int(request.json.get('score', 0)) * multiplier
    
    user_score = GameScore.query.filter_by(username=current_user).first()
    if not user_score: 
        db.session.add(GameScore(username=current_user, dino=score))
    else:
        current_best = getattr(user_score, 'dino', 0)
        if current_best is None: current_best = 0
        if score > current_best: 
            user_score.dino = score
    db.session.commit()
    return {"status": "success"}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)
