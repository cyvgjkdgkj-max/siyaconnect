from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os
import secrets


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "siya-connect-secret-key"
)


DB_PATH = "laundry.db"





def db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn



def init_db():

    conn = db()


    # =========================
    # ORDERS TABLE
    # =========================

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

        payment_method TEXT,

        status TEXT DEFAULT 'Pickup Requested',

        notes TEXT,

        created_at TEXT,

        user_id INTEGER

    )
    """)



    # =========================
    # USERS TABLE
    # =========================

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        role TEXT NOT NULL,

        full_name TEXT,

        phone TEXT

    )
    """)



    # =========================
    # NOTIFICATIONS TABLE
    # =========================

    conn.execute("""
    CREATE TABLE IF NOT EXISTS notifications (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER NOT NULL,

        message TEXT NOT NULL,

        created_at TEXT,

        is_read INTEGER DEFAULT 0

    )
    """)



    # =========================
    # DEFAULT STAFF USERS
    # =========================

    default_users = [

        (
            "admin",
            "admin123",
            "Admin",
            "System Administrator",
            ""
        ),

        (
            "driver1",
            "driver123",
            "Driver",
            "Driver One",
            ""
        ),

        (
            "laundry1",
            "laundry123",
            "Laundry",
            "Laundry Staff",
            ""
        ),

        (
            "delivery1",
            "delivery123",
            "Delivery",
            "Delivery Staff",
            ""
        )

    ]


    for username, password, role, full_name, phone in default_users:


        user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username=?
            """,
            (username,)
        ).fetchone()



        if not user:

            conn.execute(
                """
                INSERT INTO users
                (
                    username,
                    password,
                    role,
                    full_name,
                    phone
                )

                VALUES (?,?,?,?,?)

                """,
                (
                    username,
                    generate_password_hash(password),
                    role,
                    full_name,
                    phone
                )
            )



    conn.commit()

    conn.close()

init_db()

def make_order_no():

    while True:

        date = datetime.now().strftime("%y%m%d")

        code = secrets.token_hex(3).upper()

        order_no = f"LD-{date}-{code}"

        conn = db()

        exists = conn.execute(
            """
            SELECT id
            FROM orders
            WHERE order_no=?
            """,
            (order_no,)
        ).fetchone()

        conn.close()


        if not exists:
            return order_no

def create_notification(user_id, message):

    conn = db()

    conn.execute(
        """
        INSERT INTO notifications
        (
            user_id,
            message,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            message,
            datetime.now().isoformat(
                timespec="minutes"
            )
        )
    )

    conn.commit()
    conn.close()


@app.route("/")
def home():

     return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

     if request.method == "POST":

        full_name = request.form["full_name"]
        phone = request.form["phone"]
        username = request.form["username"]
        password = generate_password_hash(
     request.form["password"]
)

        conn = db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (username, password, full_name, phone, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    password,
                    full_name,
                    phone,
                    "Customer"
                )
            )

            conn.commit()
            conn.close()

            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()
            flash("Username already exists.")


     return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

       

        username = request.form.get("username")
        password = request.form.get("password")

        

        conn = db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username=?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            if user["role"] == "Admin":
                return redirect(url_for("admin"))

            elif user["role"] == "Driver":
                return redirect(url_for("driver"))

            elif user["role"] == "Laundry":
                return redirect(url_for("laundry"))

            elif user["role"] == "Delivery":
                return redirect(url_for("delivery"))

            elif user["role"] == "Customer":
                return redirect(url_for("customer_dashboard"))

        else:
            flash("Invalid username or password")

    return render_template("login.html")

    
@app.route("/pricing")
def pricing():

    return render_template("pricing.html")


@app.route("/order", methods=["GET","POST"])
def order():

    if "user_id" not in session:
        flash("Please login before placing an order.")
        return redirect(url_for("login"))

    if request.method == "POST":


        customer_name = session.get("full_name")

        phone = request.form["phone"].strip()

        address = request.form["address"].strip()

        pickup_date = request.form["pickup_date"]

        pickup_time = request.form["pickup_time"]

        service = request.form["service"]

        estimated_kg = float(
            request.form.get("estimated_kg") or 0
        )

        price = float(
            request.form.get("price") or 0
        )

        payment_method = request.form["payment_method"]

        notes = request.form.get(
            "notes",
            ""
        )


        order_no = make_order_no()

        

        user_id = session["user_id"]


        conn = db()


        conn.execute(
            """
            INSERT INTO orders
            (
                order_no,
                customer_name,
                phone,
                address,
                pickup_date,
                pickup_time,
                service,
                estimated_kg,
                price,
                payment_method,
                status,
                notes,
                created_at,
                user_id
            )

            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)

            """,
            (
                order_no,
                customer_name,
                phone,
                address,
                pickup_date,
                pickup_time,
                service,
                estimated_kg,
                price,
                payment_method,
                "Pickup Requested",
                notes,
                datetime.now().isoformat(
                    timespec="minutes"
                ),
                user_id
            )
        )


        conn.commit()

        conn.close()


        create_notification(
            user_id,
            f"Your laundry order {order_no} has been received. Status: Pickup Requested."
        )


        return redirect(
            url_for(
                "confirmation",
                order_no=order_no
            )
        )


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    return render_template(
        "order.html",
        today=today
    )
        



@app.route("/confirmation/<order_no>")
def confirmation(order_no):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = db()

    order = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE order_no=?
        AND user_id=?
        """,
        (
            order_no,
            session["user_id"]
        )
    ).fetchone()

    conn.close()

    if not order:
        return "Order not found",404


    return render_template(
        "confirmation.html",
        order=order
    )




@app.route("/track", methods=["GET", "POST"])
def track():

    if "user_id" not in session:
        flash("Please login to track your order.")
        return redirect(url_for("login"))

    order = None
    order_no = request.args.get("order_no")

    if order_no:

        conn = db()

        order = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE order_no=?
            AND user_id=?
            """,
            (
                order_no,
                session.get("user_id")
            )
        ).fetchone()

        conn.close()


    elif request.method == "POST":

        order_no = request.form.get("order_no","").strip().upper()


        conn = db()

        order = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE order_no=?
            AND user_id=?
            """,
            (
                order_no,
                session.get("user_id")
            )
        ).fetchone()

        conn.close()


        if not order:
            flash("Order number not found.")


    return render_template(
        "track.html",
        order=order
    )


@app.route("/admin")

def admin():

    if "username" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    search = request.args.get("search","").strip()

    status = request.args.get("status","")


    conn = db()


    query = """
    SELECT * FROM orders
    WHERE 1=1
    """

    params = []


    if search:

        query += """
        AND (
            order_no LIKE ?
            OR customer_name LIKE ?
            OR phone LIKE ?
        )
        """

        value = f"%{search}%"

        params.extend([
            value,
            value,
            value
        ])


    if status:

        query += """
        AND status=?
        """

        params.append(status)


    query += """
    ORDER BY id DESC
    """


    orders = conn.execute(
        query,
        params
    ).fetchall()



    total_orders = conn.execute(
        """
        SELECT COUNT(*) FROM orders
        """
    ).fetchone()[0]



    total_revenue = conn.execute(
        """
        SELECT SUM(price) FROM orders
        """
    ).fetchone()[0] or 0



    pending_orders = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status != 'Delivered'
        """
    ).fetchone()[0]



    completed_orders = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Delivered'
        """
    ).fetchone()[0]



    conn.close()



    return render_template(
        "admin.html",
        orders=orders,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        search=search,
        status=status
)





@app.post("/admin/status/<int:order_id>")
def update_status(order_id):

    if "username" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    status = request.form["status"]



    allowed = [

        "Pickup Requested",

        "Collected",

        "At Laundry",

        "Ready for Delivery",

        "Out for Delivery",

        "Delivered",

        "Cancelled"

    ]



    if status not in allowed:

        return "Invalid Status",400



    conn = db()



    conn.execute(
        """
        UPDATE orders
        SET status=?
        WHERE id=?
        """,
        (
            status,
            order_id
        )
    )



    conn.commit()

    conn.close()



    return redirect(
    url_for("admin")
)





@app.route("/print/<order_no>")
def print_order(order_no):

    conn = db()

    order = conn.execute(
        """
        SELECT * FROM orders
        WHERE order_no=?
        """,
        (order_no,)
    ).fetchone()

    conn.close()

    if not order:

        return "Order not found",404


    return render_template(
        "print_order.html",
        order=order
    )

@app.route("/customer")
def customer_dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Customer":
        return "Access Denied",403


    conn = db()

    orders = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()


    total_orders = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE user_id=?
        """,
        (session["user_id"],)
    ).fetchone()[0]


    active_orders = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE user_id=?
        AND status != 'Delivered'
        """,
        (session["user_id"],)
    ).fetchone()[0]


    completed_orders = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE user_id=?
        AND status='Delivered'
        """,
        (session["user_id"],)
    ).fetchone()[0]


    conn.close()


    return render_template(
        "customer_dashboard.html",
        orders=orders,
        full_name=session.get("full_name"),
        total_orders=total_orders,
        active_orders=active_orders,
        completed_orders=completed_orders
    )
    





@app.get("/api/orders/<order_no>")
def api_order(order_no):

    if "user_id" not in session:
        return jsonify({
            "error":"Login required"
        }),401


    conn = db()

    order = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE order_no=?
        AND user_id=?
        """,
        (
            order_no.upper(),
            session["user_id"]
        )
    ).fetchone()

    conn.close()


    if not order:
        return jsonify({
            "error":"Order not found"
        }),404


    return jsonify(dict(order))


@app.route("/driver")

def driver():

    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Driver":
        return "Access Denied",403



    conn = db()


    orders = conn.execute(
        """
        SELECT * FROM orders
        WHERE status IN (
            'Pickup Requested',
            'Collected'
        )

        ORDER BY pickup_date,pickup_time
        """
    ).fetchall()


    conn.close()



    return render_template(
        "driver.html",
        orders=orders
    )





@app.post("/driver/status/<int:order_id>")
def driver_status(order_id):


    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Driver":
        return "Access Denied",403



    status = request.form["status"]



    if status != "Collected":
        return "Invalid status",400



    conn = db()


    conn.execute(
        """
        UPDATE orders
        SET status=?
        WHERE id=?
        """,
        (
            status,
            order_id
        )
    )


    conn.commit()

    conn.close()



    return redirect(
        url_for("driver")
    )





@app.route("/laundry")


def laundry():

    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Laundry":
        return "Access Denied",403



    conn = db()



    orders = conn.execute(
        """
        SELECT * FROM orders

        WHERE status IN (
            'Collected',
            'At Laundry'
        )

        ORDER BY pickup_date,pickup_time
        """
    ).fetchall()



    conn.close()



    return render_template(
        "laundry.html",
        orders=orders
    )





@app.post("/laundry/status/<int:order_id>")
def laundry_status(order_id):


    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Laundry":
        return "Access Denied",403



    status = request.form["status"]



    allowed = [

        "At Laundry",

        "Ready for Delivery"

    ]



    if status not in allowed:

        return "Invalid status",400



    conn = db()



    conn.execute(
        """
        UPDATE orders
        SET status=?
        WHERE id=?
        """,
        (
            status,
            order_id
        )
    )



    conn.commit()

    conn.close()



    return redirect(
        url_for("laundry")
    )

@app.route("/delivery")


def delivery():
    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Delivery":
        return "Access Denied",403



    conn = db()


    orders = conn.execute(
        """
        SELECT * FROM orders

        WHERE status IN (
            'Ready for Delivery',
            'Out for Delivery'
        )

        ORDER BY pickup_date,pickup_time
        """
    ).fetchall()



    conn.close()



    return render_template(
        "delivery.html",
        orders=orders
    )





@app.post("/delivery/status/<int:order_id>")
def delivery_status(order_id):


    if "username" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Delivery":
        return "Access Denied",403



    status = request.form["status"]



    allowed = [

        "Out for Delivery",

        "Delivered"

    ]



    if status not in allowed:

        return "Invalid status",400



    conn = db()



    conn.execute(
        """
        UPDATE orders
        SET status=?
        WHERE id=?
        """,
        (
            status,
            order_id
        )
    )



    conn.commit()

    conn.close()



    return redirect(
        url_for("delivery")
    )





@app.route("/staff")
def staff():

    if "username" not in session:
        return redirect(url_for("login"))

    if session["role"] not in [
        "Admin",
        "Driver",
        "Laundry",
        "Delivery"
    ]:
        return "Access Denied",403


    conn = db()

    orders = conn.execute(
        """
        SELECT * FROM orders
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()


    return render_template(
        "staff.html",
        username=session["username"],
        role=session["role"],
        orders=orders
    )

@app.route("/staff/update/<int:order_id>", methods=["POST"])
def staff_update(order_id):

    if "username" not in session:
        return redirect(url_for("login"))


    if session.get("role") not in [
         "Admin",
         "Driver",
         "Laundry",
         "Delivery"
    ]:
      return "Access Denied", 403

    
    status = request.form["status"]

    allowed = [
        "Pickup Requested",
        "Collected",
        "At Laundry",
        "Ready for Delivery",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]

    if status not in allowed:
        return "Invalid Status", 400


    conn = db()

    conn.execute(
        """
        UPDATE orders
        SET status=?
        WHERE id=?
        """,
        (
            status,
            order_id
        )
    )

    conn.commit()
    conn.close()


    return redirect(url_for("staff"))



@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )








if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)