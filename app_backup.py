pwfrom flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DB_PATH = os.environ.get("DB_PATH", "laundry.db")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")

import os

print("Current folder:", os.getcwd())
print("Templates folder:", app.template_folder)
print("Files inside templates:")

templates_path = os.path.join(os.getcwd(), "templates")

if os.path.exists(templates_path):
    print(os.listdir(templates_path))
else:
    print("templates folder DOES NOT EXIST!")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            pickup_date TEXT NOT NULL,
            pickup_time TEXT NOT NULL,
            service TEXT NOT NULL,
            estimated_kg REAL DEFAULT 0,
            price REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'Cash on Delivery',
            status TEXT DEFAULT 'Pickup Requested',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def make_order_no():
    stamp = datetime.now().strftime("%y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"LD-{stamp}-{suffix}"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        customer_name = request.form["customer_name"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        pickup_date = request.form["pickup_date"]
        pickup_time = request.form["pickup_time"]
        service = request.form["service"]
        estimated_kg = float(request.form.get("estimated_kg") or 0)
        price = float(request.form.get("price") or 0)
        payment_method = request.form["payment_method"]
        notes = request.form.get("notes", "").strip()

        order_no = make_order_no()
        conn = db()
        conn.execute("""
            INSERT INTO orders (
                order_no, customer_name, phone, address, pickup_date,
                pickup_time, service, estimated_kg, price,
                payment_method, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no, customer_name, phone, address, pickup_date,
            pickup_time, service, estimated_kg, price,
            payment_method, "Pickup Requested", notes,
            datetime.now().isoformat(timespec="minutes")
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("confirmation", order_no=order_no))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("order.html", today=today)


@app.route("/confirmation/<order_no>")
def confirmation(order_no):
    conn = db()
    row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    conn.close()
    if not row:
        return "Order not found", 404
    return render_template("confirmation.html", order=row)


@app.route("/track", methods=["GET", "POST"])
def track():
    row = None
    if request.method == "POST":
        order_no = request.form["order_no"].strip().upper()
        conn = db()
        row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
        conn.close()
        if not row:
            flash("Order number not found.")
    return render_template("track.html", order=row)


@app.route("/admin")
def admin():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return render_template("admin_login.html")
    conn = db()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", orders=orders, admin_key=ADMIN_KEY)


@app.post("/admin/status/<int:order_id>")
def update_status(order_id):
    key = request.form.get("key", "")
    if key != ADMIN_KEY:
        return "Unauthorized", 401

    status = request.form["status"]
    valid = [
        "Pickup Requested",
        "Collected",
        "At Laundry",
        "Ready for Delivery",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]
    if status not in valid:
        return "Invalid status", 400

    conn = db()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin", key=ADMIN_KEY))


@app.route("/print/<order_no>")
def print_order(order_no):
    conn = db()
    row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    conn.close()
    if not row:
        return "Order not found", 404
    return render_template("print_order.html", order=row)


@app.get("/api/orders/<order_no>")
def api_order(order_no):
    conn = db()
    row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no.upper(),)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
