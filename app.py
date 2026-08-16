import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

import db
import pdf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-not-secret")

db.init_db()


def dollars_to_cents(raw):
    cleaned = raw.replace(",", "").replace("$", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"'{raw}' is not a valid dollar amount")
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_dollars_str(cents):
    return f"{cents / 100:,.2f}"


app.jinja_env.filters["money"] = cents_to_dollars_str


@app.route("/")
def register():
    filters = {
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
        "type": request.args.get("type", "").strip(),
        "check_from": request.args.get("check_from", "").strip(),
        "check_to": request.args.get("check_to", "").strip(),
        "q": request.args.get("q", "").strip(),
    }
    transactions = db.list_transactions(filters)
    balance_cents = db.get_current_balance_cents()
    return render_template(
        "register.html", transactions=transactions, balance_cents=balance_cents, filters=filters
    )


@app.route("/checks/new", methods=["GET", "POST"])
def new_check():
    if request.method == "POST":
        try:
            amount_cents = dollars_to_cents(request.form["amount"])
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("new_check"))
        try:
            db.insert_check(
                date=request.form["date"],
                amount_cents=amount_cents,
                description=request.form["pay_to"].strip(),
                check_number=request.form["check_number"].strip() or None,
                memo=request.form.get("memo", "").strip(),
            )
        except db.DuplicateCheckNumberError as e:
            flash(str(e))
            return redirect(url_for("new_check"))
        return redirect(url_for("register"))
    return render_template(
        "new_check.html", next_check_number=db.get_next_check_number(), today=date.today().isoformat()
    )


@app.route("/deposits/new", methods=["GET", "POST"])
def new_deposit():
    if request.method == "POST":
        try:
            amount_cents = dollars_to_cents(request.form["amount"])
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("new_deposit"))
        db.insert_deposit(
            date=request.form["date"],
            amount_cents=amount_cents,
            description=request.form["description"].strip(),
        )
        return redirect(url_for("register"))
    return render_template("new_deposit.html", today=date.today().isoformat())


@app.route("/transactions/<int:txn_id>/void", methods=["POST"])
def void_transaction(txn_id):
    if db.get_transaction(txn_id) is None:
        abort(404)
    db.toggle_void(txn_id)
    return redirect(url_for("register"))


@app.route("/transactions/<int:txn_id>/print")
def print_transaction(txn_id):
    txn = db.get_transaction(txn_id)
    if txn is None:
        abort(404)
    if txn["type"] != "check":
        abort(400)
    pdf_bytes = pdf.render_check_pdf(txn)
    db.mark_printed(txn_id)
    filename = f"check-{txn['check_number'] or txn_id}.pdf"
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=False, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
