from flask import Flask, render_template, redirect, url_for, session
from threading import Lock
import os

app = Flask(__name__)
app.secret_key = "qwertz123"  # Unbedingt ändern!

current_number = 0
next_number = 1
lock = Lock()


@app.route("/")
def home():
    return redirect(url_for("customer"))


# -------------------------------------------------
# Kundenansicht – nur Nummer ziehen
# -------------------------------------------------
@app.route("/customer")
def customer():
    global current_number
    return render_template("customer.html", current_number=current_number)


@app.route("/take_number")
def take_number():
    global next_number

    # Prüfen, ob der Nutzer schon eine Nummer gezogen hat
    if 'ticket' in session:
        ticket = session['ticket']
    else:
        with lock:
            ticket = next_number
            next_number += 1
        session['ticket'] = ticket  # Nummer in Session speichern

    return render_template("take_number.html", ticket=ticket)


# -------------------------------------------------
# Adminansicht – Nummer ziehen + Nächster Kunde
# -------------------------------------------------
@app.route("/admin")
def admin():
    global current_number, next_number

    next_customer_number = current_number + 1 if current_number < next_number else "-"

    return render_template(
        "admin.html",
        current_number=current_number,
        next_customer_number=next_customer_number,
        next_free_number=next_number,
    )


@app.route("/next_customer")
def next_customer():
    global current_number, next_number
    with lock:
        if current_number < next_number - 1:
            current_number += 1
    return redirect(url_for("admin"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
