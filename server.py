from flask import Flask, render_template, redirect, url_for
from threading import Lock

app = Flask(__name__)

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
    with lock:
        ticket = next_number
        next_number += 1
    return render_template("take_number.html", ticket=ticket)


# -------------------------------------------------
# Adminansicht – Nummer ziehen + Nächster Kunde
# -------------------------------------------------
@app.route("/admin")
def admin():
    global current_number, next_number

    # KORREKT: nächste Kundennummer ist current_number + 1
    next_customer_number = current_number + 1 if current_number < next_number else "-"

    return render_template(
        "admin.html",
        current_number=current_number,
        next_customer_number=next_customer_number,
        next_free_number=next_number,  # zur Info für Admin
    )


@app.route("/next_customer")
def next_customer():
    global current_number, next_number
    with lock:
        if current_number < next_number - 1:
            current_number += 1
    return redirect(url_for("admin"))


# -------------------------------------------------
# Starten
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)