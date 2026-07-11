from flask import Flask, render_template
from supabase import create_client, Client

app = Flask(__name__)

# Supabase Verbindung aufbauen (Ersetze mit deinen echten Daten)
SUPABASE_URL = "DEINE_SUPABASE_URL"
SUPABASE_KEY = "DEIN_SUPABASE_ANON_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/mini-youtube')
def youtube():
    # Holt alle Videos aus der Supabase-Tabelle
    response = supabase.table("videos").select("*").execute()
    video_liste = response.data  # Das ist eine Liste von dicts
    
    return render_template('watch.html', videos=video_liste)

if __name__ == '__main__':
    app.run(debug=True)
