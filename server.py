from flask import Flask, render_template, redirect, url_for, session
from threading import Lock
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "qwertz123"  # unbedingt ändern!

DB_FILE = "numbers.db"
lock = Lock()

# -------------------------------------------------
# Datenbank initialisieren
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
    # Prüfen, ob bereits ein Datensatz existiert, sonst initialisieren
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
    
    # Prüfen, ob die gespeicherte Nummer noch gültig ist
    if 'ticket' in session:
        if session['ticket'] >= next_number:
            session.pop('ticket', None)  # alte Nummer löschen
    
    return render_template("customer.html", current_number=current_number)



@app.route("/take_number")
def take_number():
    # Prüfen, ob der Nutzer schon eine Nummer gezogen hat
    if 'ticket' in session:
        ticket = session['ticket']
    else:
        with lock:
            current_number, next_number = get_numbers()
            ticket = next_number
            next_number += 1
            set_numbers(current_number, next_number)
        session['ticket'] = ticket  # Nummer in Session speichern

    return render_template("take_number.html", ticket=ticket)

# -------------------------------------------------
# Admin neue Nummer ziehen – immer neue Nummer
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
# Adminansicht – Nummer ziehen + Nächster Kunde
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
    return redirect(url_for("admin"))


from flask import session

@app.route("/reset")
def reset():
    """Setzt Zähler zurück und löscht die Session des aktuellen Kunden"""
    with lock:
        set_numbers(0, 1)
    session.pop('ticket', None)  # Session des aktuellen Benutzers löschen
    return redirect(url_for("admin"))


# -------------------------------------------------
# Starten
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
