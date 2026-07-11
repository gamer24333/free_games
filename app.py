from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# 1. Die Liste deiner Klassenkameraden (achte auf exakte Schreibweise!)
KLASSEN_LISTE = ["Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard"]

VIDEO_SAMMLUNG = [
    {"title": "Cooler Gaming Clip", "youtube_id": "dQw4w9WgXcQ", "category": "Gaming"},
    {"title": "Geometry Dash Pro", "youtube_id": "dQw4w9WgXcQ", "category": "Unterhaltung"}
]

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eingabe_name = request.form.get('nutzername').strip()
        
        # Prüfen, ob der Name in der Klassenliste ist
        if eingabe_name in KLASSEN_LISTE:
            session['username'] = eingabe_name  # Name in der Session merken
            return redirect(url_for('dashboard'))
        else:
            # Wenn der Name nicht existiert, zeigen wir einen Fehler
            return render_template('login.html', fehler="Du bist leider nicht auf der Gästeliste!")
            
    return render_template('login.html')

@app.route('/welcome')
def dashboard():
    # Schutz: Wenn man nicht eingeloggt ist, zurück zum Login
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['username'])

@app.route('/mini-youtube')
def youtube():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('watch.html', videos=VIDEO_SAMMLUNG)

@app.route('/geometry-dash')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('game.html')

# Logout-Funktion, falls sich jemand abmelden will
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
