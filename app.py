from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os
import secrets


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "siya-connect-secret-key"
)

print("App root:", app.root_path)
print("Template folder:", app.template_folder)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Frame-Options"] = "DENY"
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "laundry.db")

@app.before_request
def check_session():

    public_routes = [
    "home",
    "login",
    "register",
    "staff_login",
    "logout",
    "pricing",
    "how_it_works",
    "static"
]

    if request.endpoint and request.endpoint not in public_routes:

        if "user_id" not in session:
            return redirect(url_for("login"))


def db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn



def init_db():

    conn = db()

    conn.execute("""
CREATE TABLE IF NOT EXISTS status_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    status TEXT NOT NULL,

    changed_by INTEGER,

    changed_at TEXT,

    FOREIGN KEY(order_id) REFERENCES orders(id)

)
""")

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

        payment_status TEXT DEFAULT 'Pending',

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

        phone TEXT,
        
        address TEXT

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


def update_database():

    conn = db()

    try:
        conn.execute(
            """
            ALTER TABLE orders
            ADD COLUMN payment_status TEXT DEFAULT 'Pending'
            """
        )

        conn.commit()

    except sqlite3.OperationalError:
        pass

    conn.close()


update_database()



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
            datetime.now().isoformat(timespec="minutes")
        )
    )

    conn.commit()
    conn.close()



def save_status_history(order_id, status, changed_by):

    conn = db()

    conn.execute(
        """
        INSERT INTO status_history
        (
            order_id,
            status,
            changed_by,
            changed_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            order_id,
            status,
            changed_by,
            datetime.now().isoformat(timespec="minutes")
        )
    )

    conn.commit()
    conn.close()

def update_order_status(order_id, status, changed_by):

    conn = db()

    order = conn.execute(
        """
        SELECT user_id, order_no
        FROM orders
        WHERE id=?
        """,
        (order_id,)
    ).fetchone()


    if not order:
        conn.close()
        return False


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


    if order["user_id"]:

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
                order["user_id"],
                f"Your order {order['order_no']} status changed to {status}",
                datetime.now().isoformat(timespec="minutes")
            )
        )


    conn.commit()
    conn.close()


    save_status_history(
        order_id,
        status,
        changed_by
    )


    return True

@app.route("/")
def home():

     return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

     if request.method == "POST":

        full_name = request.form["full_name"]



        phone = request.form["phone"]
        address = request.form["address"]
        username = request.form["username"]
        password = generate_password_hash(
     request.form["password"]
    )

        conn = db()

        try:

            conn.execute(
    """
    INSERT INTO users
    (
        username,
        password,
        full_name,
        phone,
        address,
        role
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        username,
        password,
        full_name,
        phone,
        address,
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

@app.route("/staff-login", methods=["GET","POST"])
def staff_login():

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


        if user and user["role"] != "Customer" and check_password_hash(
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


        else:

            flash("Invalid staff login")


    return render_template("staff_login.html")

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("login"))
    
@app.route("/pricing")
def pricing():

    return render_template("pricing.html")

@app.route("/how-it-works")
def how_it_works():

    return render_template("how_it_works.html")

@app.route("/order", methods=["GET", "POST"])
def order():

    if "user_id" not in session:
        flash("Please login before placing an order.")
        return redirect(url_for("login"))


    if request.method == "POST":

        customer_name = session.get("full_name")

        phone = request.form.get("phone")
        address = request.form.get("address")

        pickup_date = request.form["pickup_date"]
        pickup_time = request.form["pickup_time"]

        service = request.form["service"]


        try:
            estimated_kg = float(
                request.form.get("estimated_kg") or 0
            )

        except ValueError:
            flash("Invalid weight")
            return redirect(url_for("order"))


        rates = {
            "Wash & Fold":25,
            "Ironing":15,
            "Dry Cleaning":40,
            "Express Laundry":50
        }


        if service not in rates:
            flash("Invalid service")
            return redirect(url_for("order"))


        price = estimated_kg * rates[service]


        payment_method = request.form.get("payment_method")

        notes = request.form.get("notes","")


        order_no = make_order_no()


        conn = db()


        cursor = conn.execute(
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
        payment_status,
        status,
        notes,
        created_at,
        user_id
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

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
        "Pending",
        "Pickup Requested",
        notes,
        datetime.now().isoformat(timespec="minutes"),
        session["user_id"]
        )
        )


        order_id = cursor.lastrowid


        conn.commit()
        conn.close()


        save_status_history(
            order_id,
            "Pickup Requested",
            session["user_id"]
        )


        create_notification(
            session["user_id"],
            f"Your laundry order {order_no} has been received."
        )


        return redirect(
            url_for(
                "confirmation",
                order_no=order_no
            )
        )


    today = datetime.now().strftime("%Y-%m-%d")


    return render_template(
        "order.html",
        today=today
    )

@app.route("/walk-in-order", methods=["GET", "POST"])
def walk_in_order():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] not in [
        "Admin",
        "Laundry"
    ]:
        return "Access Denied", 403


    if request.method == "POST":

        customer_name = request.form["customer_name"]
        phone = request.form["phone"]
        address = request.form["address"]

        pickup_date = request.form.get(
            "pickup_date",
            datetime.now().strftime("%Y-%m-%d")
        )

        pickup_time = request.form.get(
            "pickup_time",
            "Walk-in"
        )

        service = request.form["service"]

        estimated_kg = float(
            request.form.get("estimated_kg") or 0
        )


        rates = {
            "Wash & Fold": 25,
            "Ironing": 15,
            "Dry Cleaning": 40,
            "Express Laundry": 50
        }


        if service not in rates:
            flash("Invalid service selected.")
            return redirect(url_for("walk_in_order"))


        price = estimated_kg * rates[service]


        payment_method = request.form.get(
            "payment_method",
            "Cash"
        )

        notes = request.form.get(
            "notes",
            "Walk-in customer"
        )


        order_no = make_order_no()


        conn = db()


        cursor = conn.execute(
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
                payment_status,
                status,
                notes,
                created_at,
                user_id
            )

            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

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
                "Pending",
                "Pickup Requested",
                notes,
                datetime.now().isoformat(timespec="minutes"),
                session["user_id"]
            )
        )


        order_id = cursor.lastrowid


        conn.commit()
        conn.close()


        save_status_history(
            order_id,
            "Pickup Requested",
            session["user_id"]
        )


        flash("Walk-in order created successfully.")


        return redirect(
            url_for("admin")
        )


    return render_template(
        "walk_in_order.html"
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
        """,
        (order_no,)
    ).fetchone()

    conn.close()

    if not order:
        return "Order not found",404


    return render_template(
        "confirmation.html",
        order=order
    )
    
@app.route("/history/<order_no>")
def history(order_no):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = db()

    order = conn.execute("""
        SELECT *
        FROM orders
        WHERE order_no=?
        AND user_id=?
    """, (order_no, session["user_id"])).fetchone()

    if not order:
        conn.close()
        return "Order not found", 404

    history = conn.execute("""
        SELECT *
        FROM status_history
        WHERE order_id=?
        ORDER BY id ASC
    """, (order["id"],)).fetchall()

    conn.close()

    return render_template(
        "history.html",
        order=order,
        history=history
    )


@app.route("/track/<order_no>")
def track(order_no):

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
        "track.html",
        order=order
    )
@app.route("/customer/<int:user_id>")
def customer_profile(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    conn = db()

    customer = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id=?
        AND role='Customer'
        """,
        (user_id,)
    ).fetchone()


    orders = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()


    conn.close()


    return render_template(
        "customer_profile.html",
        customer=customer,
        orders=orders
    )

@app.route("/customer_dashboard")
def customer_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Customer":
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


    notifications = conn.execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()


    total_orders = len(orders)


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
        full_name=session["full_name"],
        orders=orders,
        notifications=notifications,
        total_orders=total_orders,
        active_orders=active_orders,
        completed_orders=completed_orders
    )
@app.route("/customers")
def customers():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    conn = db()

    customers = conn.execute(
        """
        SELECT 
            users.id,
            users.full_name,
            users.phone,
            users.address,
            COUNT(orders.id) AS total_orders,
            COALESCE(SUM(orders.price),0) AS total_spent

        FROM users

        LEFT JOIN orders
        ON users.id = orders.user_id

        WHERE users.role='Customer'

        GROUP BY users.id

        ORDER BY users.id DESC
        """
    ).fetchall()


    conn.close()


    return render_template(
    "customers.html",
    customers=customers
)

@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    search = request.args.get("search","").strip()

    status = request.args.get("status","")


    conn = db()


    query = """
    SELECT *
    FROM orders
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
        SELECT COUNT(*)
        FROM orders
        """
    ).fetchone()[0]



    total_revenue = conn.execute(
        """
        SELECT COALESCE(SUM(price),0)
        FROM orders
        """
    ).fetchone()[0]



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



    total_customers = conn.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role='Customer'
        """
    ).fetchone()[0]



    pickup_requests = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Pickup Requested'
        """
    ).fetchone()[0]



    at_laundry = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='At Laundry'
        """
    ).fetchone()[0]



    out_for_delivery = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Out for Delivery'
        """
    ).fetchone()[0]



    delivered_today = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='Delivered'
        AND DATE(created_at)=DATE('now')
        """
    ).fetchone()[0]



    monthly_revenue = conn.execute(
        """
        SELECT COALESCE(SUM(price),0)
        FROM orders
        WHERE strftime('%Y-%m', created_at)
        =
        strftime('%Y-%m','now')
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

        total_customers=total_customers,

        pickup_requests=pickup_requests,

        at_laundry=at_laundry,

        out_for_delivery=out_for_delivery,

        delivered_today=delivered_today,

        monthly_revenue=monthly_revenue,

        search=search,

        status=status
    )


@app.post("/admin/status/<int:order_id>")
def update_status(order_id):

    if "user_id" not in session:
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


    success = update_order_status(
        order_id,
        status,
        session["user_id"]
    )


    if not success:
        return "Order not found",404


    flash("Order status updated successfully.")

    return redirect(url_for("admin"))

@app.post("/admin/payment/<int:order_id>")
def payment_status(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Admin":
        return "Access Denied",403


    payment_status = request.form["payment_status"]


    allowed = [
        "Pending",
        "Paid",
        "Failed",
        "Refunded"
    ]


    if payment_status not in allowed:
        return "Invalid payment status",400


    conn = db()

    conn.execute(
        """
        UPDATE orders
        SET payment_status=?
        WHERE id=?
        """,
        (
            payment_status,
            order_id
        )
    )

    conn.commit()
    conn.close()


    flash("Payment status updated.")

    return redirect(url_for("admin"))

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

    

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Driver":
        print("WRONG ROLE:", session.get("role"))
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

    today = datetime.now().strftime("%d %b %Y")

    return render_template(
    "driver.html",
    orders=orders,
    today=today
)


@app.post("/driver/status/<int:order_id>")
def driver_status(order_id):


    if "user_id" not in session:
        return redirect(url_for("login"))


    if session["role"] != "Driver":
        return "Access Denied",403



    status = request.form["status"]



    if status != "Collected":
        return "Invalid status",400



    update_order_status(
    order_id,
    status,
    session["user_id"]
)

    return redirect(url_for("driver"))


@app.route("/laundry")
def laundry():

    if "user_id" not in session:
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

    

    today = datetime.now().strftime("%d %b %Y")

    return render_template(
    "laundry.html",
    orders=orders,
    today=today
)





@app.post("/laundry/status/<int:order_id>")
def laundry_status(order_id):


    if "user_id" not in session:
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


    update_order_status(
       order_id,
       status,
       session["user_id"]
    )

    return redirect(url_for("laundry"))


@app.route("/delivery")
def delivery():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Delivery":
        return "Access Denied", 403

    conn = db()

    orders = conn.execute("""
        SELECT *
        FROM orders
        WHERE status IN (
            'Ready for Delivery',
            'Out for Delivery'
        )
        ORDER BY pickup_date, pickup_time
    """).fetchall()

    ready_count = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status='Ready for Delivery'
    """).fetchone()[0]

    out_count = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status='Out for Delivery'
    """).fetchone()[0]

    delivered_count = conn.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status='Delivered'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "delivery.html",
        orders=orders,
        ready_count=ready_count,
        out_count=out_count,
        delivered_count=delivered_count,
        today=datetime.now().strftime("%d %b %Y")
    )

@app.post("/delivery/status/<int:order_id>")
def delivery_status(order_id):


    if "user_id" not in session:
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



    update_order_status(
    order_id,
    status,
    session["user_id"]
)

    return redirect(url_for("delivery"))





@app.route("/staff")
def staff():

    if "user_id" not in session:
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

    if "user_id" not in session:
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


    update_order_status(
       order_id,
       status,
       session["user_id"]
   )

    return redirect(url_for("staff"))

@app.route("/print-order/<order_no>")
def print_order(order_no):

    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = db()

    order = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE order_no=?
        """,
        (order_no,)
    ).fetchone()

    conn.close()

    if not order:
        return "Order not found", 404

    return render_template(
        "print_order.html",
        order=order
    )







if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)