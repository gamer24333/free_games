from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# 1. Die Liste deiner Klassenkameraden (achte auf exakte Schreibweise!)
KLASSEN_LISTE = ["Till", "Ben", "Matteo", "Louis", "Maxim", "Jonah P", "Jonah S", "Mateo", "Hanna", "Emma", "Lia", "Mia", "Lena S", "Lena G", "Lena D", "Dasha", "Daniel", "Bennet", "Erik", "Roman", "Janne", "Tom", "Levin", "Liam", "Tim", "Nathalie", "Richard"]

# Hier werden die Nachrichten gespeichert (solange die App läuft)
# Jede Nachricht ist ein kleines Dictionary mit Name und Text
CHAT_NACHRICHTEN = [
    {"name": "System", "text": "Willkommen im geheimen Klassen-Chat! 🤫"}
]

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ... Deine Login- und Dashboard-Routen bleiben gleich ...

@app.route('/welcome')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['username'])

# NEU: Der Klassen-Chat
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nachricht_text = request.form.get('message').strip()
        if nachricht_text:
            # Nachricht mit dem Namen des eingeloggten Nutzers speichern
            CHAT_NACHRICHTEN.append({
                "name": session['username'],
                "text": nachricht_text
            })
            # Nach dem Senden laden wir die Seite neu, um die Nachricht anzuzeigen
            return redirect(url_for('chat'))

    return render_template('chat.html', nachrichten=CHAT_NACHRICHTEN)

if __name__ == '__main__':
    app.run(debug=True)
