from flask import Flask, render_template, redirect, url_for, session, request
from flask_socketio import SocketIO, emit
from threading import Lock
import os
import sqlite3
import time
import secrets
# --- NEU: ProxyFix importieren ---
from werkzeug.middleware.proxy_fix import ProxyFix

QR_TOKEN = None
QR_TOKEN_EXPIRES = 0

def generate_qr_token():
    global QR_TOKEN, QR_TOKEN_EXPIRES
    QR_TOKEN = secrets.token_urlsafe(16)
    QR_TOKEN_EXPIRES = time.time() + 60  # Token 60 Sekunden gültig
    return QR_TOKEN

def verify_qr_token(token):
    return token == QR_TOKEN and time.time() < QR_TOKEN_EXPIRES


app = Flask(__name__)
# --- WICHTIG: ProxyFix anwenden, damit Flask die HTTPS/Host-Header von ngrok korrekt erkennt. ---
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.secret_key = "qwertz123"  # unbedingt ändern!

# --- FIX FÜR SESSIONS/COOKIES ÜBER PROXY/NGROK ---
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https'


# SocketIO initialisieren
socketio = SocketIO(app, async_mode='eventlet')

DB_FILE = "numbers.db"
lock = Lock()

# -------------------------------------------------
# Datenbank 
# -------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS counter (
            id INTEGER PRIMARY KEY,
            current_number INTEGER NOT NULL,
            next_number INTEGER NOT NULL
        )
    """)
    c.execute("SELECT COUNT(*) FROM counter")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO counter (current_number, next_number) VALUES (?, ?)", (0, 1))
    conn.commit()
    conn.close()

def get_numbers():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT current_number, next_number FROM counter WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row

def set_numbers(current_number, next_number):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE counter SET current_number=?, next_number=? WHERE id=1", (current_number, next_number))
    conn.commit()
    conn.close()

init_db()


# -------------------------------------------------
# Home
# -------------------------------------------------
@app.route("/")
def home():
    return redirect(url_for("customer"))


# -------------------------------------------------
# Kundenansicht – nur Nummer ziehen
# -------------------------------------------------
@app.route("/customer")
def customer():
    current_number, next_number = get_numbers()
    
    # Session-Ticket löschen, wenn es bereits aufgerufen wurde
    if 'ticket' in session:
        if session['ticket'] >= current_number:
            session.pop('ticket', None) 
    
    return render_template("customer.html", current_number=current_number)

# -------------------------------------------------
# NEUE SEITE: Öffentliches Display
# -------------------------------------------------
@app.route("/current-customers")
def current_customers():
    current_number, _ = get_numbers()
    return render_template("current-customers.html", current_number=current_number)


@app.route("/take_number")
def take_number():
    token = request.args.get("token", "")

    if not verify_qr_token(token):
        return "QR-Code abgelaufen. Bitte neuen QR-Code scannen.", 403

    if 'ticket' in session:
        ticket = session['ticket']
    else:
        with lock:
            current_number, next_number = get_numbers()
            ticket = next_number
            next_number += 1
            set_numbers(current_number, next_number)
        session['ticket'] = ticket

    return render_template("take_number.html", ticket=ticket)


# -------------------------------------------------
# Admin neue Nummer ziehen
# -------------------------------------------------
@app.route("/admin_take_number")
def admin_take_number():
    with lock:
        current_number, next_number = get_numbers()
        ticket = next_number
        next_number += 1
        set_numbers(current_number, next_number)
    return redirect(url_for("admin"))


# -------------------------------------------------
# Adminansicht
# -------------------------------------------------
@app.route("/admin")
def admin():
    current_number, next_number = get_numbers()
    next_customer_number = current_number + 1 if current_number < next_number else "-"

    return render_template(
        "admin.html",
        current_number=current_number,
        next_customer_number=next_customer_number,
        next_free_number=next_number,
    )


@app.route("/next_customer")
def next_customer():
    with lock:
        current_number, next_number = get_numbers()
        if current_number < next_number - 1:
            current_number += 1
            set_numbers(current_number, next_number)
            
            # Sendet das Update an alle verbundenen Clients
            socketio.emit('number_update', {'current_number': current_number})
            
    return redirect(url_for("admin"))


@app.route("/reset")
def reset():
    """Setzt Zähler zurück und löscht die Session des aktuellen Kunden"""
    with lock:
        set_numbers(0, 1)
        # Sendet Update (Reset) an alle Clients
        socketio.emit('number_update', {'current_number': 0})
        
    # Die Session wird aus dem Browser-Cookie gelöscht
    session.pop('ticket', None)
    return redirect(url_for("admin"))

@app.route("/qr")
def qr():
    token = generate_qr_token()
    url = url_for("take_number", token=token, _external=True)
    return render_template("qr.html", url=url)


# -------------------------------------------------
# Starten
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Starte den Server mit SocketIO (und eventlet)
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
