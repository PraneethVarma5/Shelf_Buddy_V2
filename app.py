from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for, Response, flash
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import requests
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import smtplib
import random
import string
from email.mime.text import MIMEText
load_dotenv()

DB_PATH = os.getenv("DATABASE_PATH", "shelfbuddy.db")
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_column_if_not_exists(cur, table, column, definition):
    cur.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cur.fetchall()]

    if column not in columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


app = Flask(__name__)

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    # PRODUCTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        shelf_life_room_closed INTEGER,
        shelf_life_room_opened INTEGER,
        shelf_life_refrigerated_closed INTEGER,
        shelf_life_refrigerated_opened INTEGER,
        shelf_life_frozen_closed INTEGER,
        shelf_life_frozen_opened INTEGER
    )
    """)

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)
    add_column_if_not_exists(cur, "users", "otp", "TEXT")
    add_column_if_not_exists(cur, "users", "otp_expiry", "TEXT")
    add_column_if_not_exists(cur, "users", "is_verified", "INTEGER DEFAULT 0")
    add_column_if_not_exists(cur, "users", "reset_token", "TEXT")
    add_column_if_not_exists(cur, "users", "reset_token_expiry", "TEXT")

    # PANTRY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pantry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product TEXT,
        expiry_date TEXT,
        UNIQUE(user_id, product, expiry_date),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # SUGGESTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # CHECK IF PRODUCTS TABLE IS EMPTY
    cur.execute("SELECT COUNT(*) FROM products")
    product_count = cur.fetchone()[0]

    if product_count == 0:
        products = [
            ("Rice", "food", 180, 90, 365, 180, 0, 0),
            ("Basmati Rice", "food", 365, 180, 365, 180, 0, 0),
            ("Brown Rice", "food", 120, 60, 240, 120, 0, 0),
            ("Wheat Flour", "food", 180, 60, 365, 180, 730, 365),
            ("Maida", "food", 180, 60, 365, 180, 730, 365),
            ("Sugar", "food", 3650, 3650, 3650, 3650, 0, 0),
            ("Salt", "food", 3650, 3650, 3650, 3650, 0, 0),
            ("Lentils", "food", 365, 180, 365, 180, 0, 0),
            ("Chickpeas", "food", 730, 365, 730, 365, 0, 0),
            ("Rajma", "food", 730, 365, 730, 365, 0, 0),
            ("Vegetable Oil", "food", 365, 180, 0, 0, 0, 0),
            ("Olive Oil", "food", 365, 180, 0, 0, 0, 0),
            ("Ghee", "food", 365, 180, 365, 180, 0, 0),
            ("Butter", "food", 1, 0, 180, 30, 365, 180),
            ("Milk", "food", 0, 0, 5, 3, 0, 0),
            ("Curd", "food", 0, 0, 14, 5, 0, 0),
            ("Cheese", "food", 0, 0, 180, 30, 240, 180),
            ("Paneer", "food", 0, 0, 5, 2, 90, 30),
            ("Onion", "food", 30, 14, 60, 14, 0, 0),
            ("Potato", "food", 60, 0, 0, 0, 0, 0),
            ("Tomato", "food", 7, 0, 14, 7, 0, 0),
            ("Apple", "food", 7, 0, 30, 15, 0, 0),
            ("Banana", "food", 3, 0, 7, 3, 0, 0),
            ("Chicken", "food", 0, 0, 2, 2, 365, 180),
            ("Fish", "food", 0, 0, 2, 2, 240, 120),
            ("Eggs", "food", 7, 0, 30, 0, 0, 0),
            ("Bread", "food", 5, 5, 14, 14, 90, 30),
            ("Biscuits", "food", 180, 30, 0, 0, 0, 0),
            ("Jam", "food", 365, 0, 365, 90, 0, 0),
            ("Honey", "food", 3650, 3650, 3650, 3650, 0, 0),
            ("Ketchup", "food", 365, 90, 365, 90, 0, 0)
        ]

        cur.executemany("""
            INSERT OR IGNORE INTO products
            (name, category,
             shelf_life_room_closed,
             shelf_life_room_opened,
             shelf_life_refrigerated_closed,
             shelf_life_refrigerated_opened,
             shelf_life_frozen_closed,
             shelf_life_frozen_opened)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-this")
CORS(app)
create_tables()
def get_shelf_life(product, storage, opened):
    storage_map = {
        'room': 'room',
        'refrigerated': 'refrigerated',
        'frozen': 'frozen'
    }

    mapped_storage = storage_map.get(storage, 'room')
    column = f"shelf_life_{mapped_storage}_{'opened' if opened else 'closed'}"
    
    conn = get_db_connection()
    cur = conn.cursor()

    query = f"""
        SELECT {column}
        FROM products
        WHERE LOWER(name) LIKE ?
    """

    search_term = f"%{product.lower()}%"
    cur.execute(query, (search_term,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result[0] if result and result[0] is not None else None

#Registration route

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Insert user
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            expiry = (datetime.now() + timedelta(minutes=5)).isoformat()

            # Update OTP fields
            cur.execute("""
                UPDATE users
                SET otp=?, otp_expiry=?, is_verified=0
                WHERE email=?
            """, (otp, expiry, email))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.rollback()
            cur.close()
            conn.close()
            flash("User already exists. Try logging in instead.", "error")
            return render_template("register.html")

        cur.close()
        conn.close()

        # Send email after DB commit
        try:
            send_email(
                email,
                "Verify Your Account - ShelfBuddy",
                f"Your OTP is {otp}. It expires in 5 minutes."
            )
        except Exception as e:
            print("REGISTER EMAIL ERROR:", str(e))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE email=?", (email,))
            conn.commit()
            cur.close()
            conn.close()

            flash("We couldn't send the OTP email right now. Please try again.", "error")
            return render_template("register.html")

        flash("OTP sent to your email. Please verify your account.", "success")
        return redirect(url_for('verify_otp', email=email))

    return render_template("register.html")

#login route

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, role, is_verified FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            flash("User not found. Please register.", "error")
            return render_template("login.html")
        if user[4] == 0:
            flash("Please verify your email first.", "error")
            return render_template("login.html")
        if not check_password_hash(user[2], password):
            flash("Incorrect password.", "error")
            return render_template("login.html")
    


        session['user_id'] = user[0]
        session['username'] = user[1]
        session['role'] = user[3]
        return redirect('/home')

    return render_template("login.html")

# Guest Mode route
@app.route('/guest')
def guest():
    session['guest'] = True
    session['user_id'] = None
    session['username'] = "Guest"
    return redirect(url_for('home'))


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('first_page'))

# Save to pantry route
@app.route('/save-to-pantry', methods=['POST'])
def save_to_pantry():

    if session.get('user_id') is None:
        return jsonify({"status": "error", "message": "Login required."})

    data = request.json
    product = data.get("product")
    expiry_date = data.get("expiry_date")

    if not product or not expiry_date:
        return jsonify({"status": "error", "message": "Invalid data."})

    conn = get_db_connection()
    cur = conn.cursor()

    # Prevent duplicates
    cur.execute("""
        SELECT id FROM pantry
        WHERE user_id=? AND product=? AND expiry_date=?
    """, (session['user_id'], product, expiry_date))

    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return jsonify({"status": "error", "message": "Item already saved."})

    cur.execute("""
        INSERT INTO pantry (user_id, product, expiry_date)
        VALUES (?, ?, ?)
    """, (session['user_id'], product, expiry_date))

    conn.commit()   # ✅ THIS WAS MISSING

    cur.close()
    conn.close()

    return jsonify({"status": "success", "message": "Saved to pantry!"})

# Pantry route to display saved items and their expiry dates, sorted by nearest expiry first
@app.route('/pantry')
def pantry():

    if not session.get('user_id'):
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, product, expiry_date
        FROM pantry
        WHERE user_id=?
        ORDER BY expiry_date ASC
    """, (session['user_id'],))

    rows = cur.fetchall()
    cur.close()
    conn.commit()
    conn.close()

    pantry_items = []
    today = datetime.now().date()

    for row in rows:
        expiry = datetime.strptime(row["expiry_date"], "%Y-%m-%d").date()
        days_left = (expiry - today).days

        pantry_items.append({
            "id": row["id"],
            "product": row["product"],
            "expiry_date": row["expiry_date"],
            "days_left": days_left
        })

    return render_template("pantry.html", items=pantry_items)

# Route to delete an item from the pantry
@app.route('/delete-from-pantry', methods=['POST'])
def delete_from_pantry():

    if not session.get('user_id'):
        return jsonify({"status": "error", "message": "Unauthorized"})

    data = request.json
    item_id = data.get("item_id")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM pantry
        WHERE id=? AND user_id=?
    """, (item_id, session['user_id']))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "success"})


#pantry stats route to show number of expired and soon-to-expire items
@app.route('/pantry-stats')
def pantry_stats():
    if not session.get('user_id'):
        return jsonify({"expired":0,"soon":0,"safe":0,"total":0})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT expiry_date FROM pantry
        WHERE user_id = ?
    """, (session['user_id'],))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    expired = soon = safe = 0
    today = datetime.now().date()
    
    for (expiry_date,) in rows:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        days = (expiry - today).days
        if days < 0:
            expired += 1
        elif days <= 3:
            soon += 1
        else:
            safe += 1

    return jsonify({
        "expired": expired,
        "soon": soon,
        "safe": safe,
        "total": expired + soon + safe
    })



# Route for robots.txt
@app.route('/robots.txt')
def serve_robots():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'robots.txt',
        mimetype='text/plain'
    )

# Route for sitemap.xml
@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(app.static_folder, 'sitemap.xml')

@app.route('/get-product', methods=['POST'])
def get_product():
    data = request.json
    product = data.get('product', '').strip()
    storage = data.get('storage', 'room')
    opened = data.get('opened', False)
    manu_date = data.get('manufacturing_date')

    if not product:
        return jsonify({'status': 'error', 'message': 'Product name is required'}), 400

    shelf_life = get_shelf_life(product, storage, opened)
    if shelf_life is None:
        return jsonify({'status': 'error', 'message': 'Product not found or shelf life missing'}), 404

    if manu_date:
        try:
            if manu_date == "Invalid Date" or manu_date.strip() == "":
                raise ValueError
            mdate = datetime.strptime(manu_date, '%Y-%m-%d')
            expiry = mdate + timedelta(days=shelf_life)
            return jsonify({
                'status': 'success',
                'expiry_date': expiry.strftime('%Y-%m-%d'),
                'shelf_life': shelf_life
            })
        except:
            return jsonify({'status': 'error', 'message': 'Invalid date'}), 400

    return jsonify({
        'status': 'success',
        'shelf_life': shelf_life
    })


@app.route('/get-category-average', methods=['POST'])
def get_category_average():
    data = request.json
    category = data.get('category')

    if not category:
        return jsonify({'status': 'error', 'message': 'Category is required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(
            shelf_life_room_closed +
            shelf_life_refrigerated_closed +
            shelf_life_frozen_closed
        ) / 3
        FROM products
        WHERE LOWER(category) = ?
    """, (category.lower(),))

    avg = cur.fetchone()[0]

    cur.close()
    conn.close()

    if avg is None:
        return jsonify({'status': 'error', 'message': 'Category not found'}), 404

    return jsonify({
        'status': 'success',
        'category': category,
        'average_shelf_life': round(avg)
    })

@app.route('/')
def first_page():
    return render_template("landing.html")

@app.route('/home')
def home():
    return render_template("main.html")

# Debug route to check users in the database
# @app.route('/debug-users')
# def debug_users():
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("SELECT id, username, email FROM users")
#     users = cur.fetchall()
#     cur.close()
#     conn.close()
#     return str(users)

@app.route('/submit-suggestion', methods=['POST'])
def submit_suggestion():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not message:
        return jsonify({"status": "error", "message": "Message required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO suggestions (name, email, message) VALUES (?, ?, ?)",
        (name, email, message)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/suggest-recipe')
def suggest_recipe():
    return render_template("suggest_recipe.html")


@app.route('/get-recipes', methods=['POST'])
def get_recipes():

    data = request.json
    offset = data.get("offset", 0)

    ingredient1 = data.get("ingredient1")
    ingredient2 = data.get("ingredient2")
    ingredient3 = data.get("ingredient3")
    cuisine = data.get("cuisine")

    ingredients = ",".join(
        [i for i in [ingredient1, ingredient2, ingredient3] if i]
    )

    
    api_key = os.getenv("SPOONACULAR_API_KEY")

    url = "https://api.spoonacular.com/recipes/complexSearch"

    params = {
        "apiKey": api_key,
        "query": ingredient1,
        "number": 4,
        "offset": offset,
        "addRecipeInformation": True
    }

    # Only add these if they exist
    if ingredients:
        params["includeIngredients"] = ingredients

    if cuisine:
        params["cuisine"] = cuisine

    response = requests.get(url, params=params)

    return jsonify(response.json())

# @app.route('/debug-suggestions')
# def debug_suggestions():
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM suggestions")
#     rows = cur.fetchall()
#     conn.close()
#     return str(rows)

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if not session.get("user_id"):
            return redirect("/login")

        if session.get("role") != "admin":
            return "Unauthorized", 403

        return f(*args, **kwargs)

    return decorated

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, email, role FROM users")
    users = cur.fetchall()

    cur.execute("SELECT id, name, category FROM products")
    products = cur.fetchall()

    cur.execute("SELECT id, name, email, message, created_at FROM suggestions ORDER BY id DESC")
    suggestions = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        products=products,
        suggestions=suggestions
    )

# def send_email(to_email, subject, body):
#     smtp_host = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
#     smtp_port = int(os.getenv("EMAIL_PORT", 587))
#     smtp_user = os.getenv("EMAIL_USER")
#     smtp_pass = os.getenv("EMAIL_PASS")
#     sender_email = os.getenv("SENDER_EMAIL", "praneeth882005@gmail.com")

#     if not smtp_user or not smtp_pass:
#         raise Exception("Email credentials not configured in .env")

#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = f"ShelfBuddy <{sender_email}>"
#     msg["To"] = to_email

#     with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
#         server.ehlo()
#         server.starttls()
#         server.ehlo()
#         server.login(smtp_user, smtp_pass)
#         server.sendmail(sender_email, to_email, msg.as_string())
def send_email(to_email, subject, body):
    smtp_host = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
    smtp_port = int(os.getenv("EMAIL_PORT", 587))
    smtp_user = os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("EMAIL_PASS")
    sender_email = os.getenv("SENDER_EMAIL", "praneeth882005@gmail.com")

    print("EMAIL DEBUG -> HOST:", smtp_host)
    print("EMAIL DEBUG -> PORT:", smtp_port)
    print("EMAIL DEBUG -> USER:", smtp_user)
    print("EMAIL DEBUG -> PASS SET:", bool(smtp_pass))
    print("EMAIL DEBUG -> SENDER:", sender_email)

    if not smtp_user or not smtp_pass:
        raise Exception("Email credentials not configured in environment variables")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"ShelfBuddy <{sender_email}>"
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.set_debuglevel(1)   # SMTP conversation in logs
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, to_email, msg.as_string())
            print("EMAIL DEBUG -> Email sent successfully")
    except Exception as e:
        print("EMAIL DEBUG -> SMTP ERROR:", repr(e))
        raise

@app.route('/resend-otp')
def resend_otp():
    email = request.args.get('email')

    if not email:
        flash("Invalid request.", "error")
        return redirect(url_for('register'))

    conn = get_db_connection()
    cur = conn.cursor()

    user = cur.execute(
        "SELECT id FROM users WHERE email=?",
        (email,)
    ).fetchone()

    if not user:
        cur.close()
        conn.close()
        flash("Invalid request.", "error")
        return redirect(url_for('register'))

    otp = str(random.randint(100000, 999999))
    expiry = (datetime.now() + timedelta(minutes=5)).isoformat()

    cur.execute("""
        UPDATE users
        SET otp=?, otp_expiry=?
        WHERE email=?
    """, (otp, expiry, email))

    conn.commit()
    cur.close()
    conn.close()
    
    try:
        send_email(
            email,
            "Your New OTP - ShelfBuddy",
            f"Your new OTP is {otp}. It expires in 5 minutes."
        )
        flash("A new OTP has been sent to your email.", "success")
    except Exception as e:
        print("RESEND OTP EMAIL ERROR:", str(e))
        flash("Couldn't resend OTP right now. Please try again.", "error")

    return redirect(url_for('verify_otp', email=email))

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')

    if not email:
        flash("Invalid verification request.", "error")
        return redirect(url_for('register'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()

        user = cur.execute(
            "SELECT otp, otp_expiry FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if not user:
            cur.close()
            conn.close()
            flash("Invalid request.", "error")
            return redirect(url_for('register'))

        stored_otp, expiry = user

        if not expiry:
            cur.close()
            conn.close()
            flash("OTP expired. Please request a new one.", "error")
            return render_template("verify_otp.html", email=email)

        expiry = datetime.fromisoformat(expiry)

        if entered_otp == stored_otp and datetime.now() < expiry:
            cur.execute("""
                UPDATE users
                SET is_verified=1, otp=NULL, otp_expiry=NULL
                WHERE email=?
            """, (email,))
            conn.commit()
            cur.close()
            conn.close()

            flash("Email verified successfully. Please login.", "success")
            return redirect(url_for('login'))

        cur.close()
        conn.close()
        flash("Invalid or expired OTP.", "error")
        return render_template("verify_otp.html", email=email)

    cur.close()
    conn.close()
    return render_template("verify_otp.html", email=email)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            flash("If the account exists, a reset link has been sent.", "success")
            return redirect(url_for('forgot_password'))

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        expiry = (datetime.now() + timedelta(minutes=15)).isoformat()

        cur.execute("""
            UPDATE users
            SET reset_token=?, reset_token_expiry=?
            WHERE email=?
        """, (token, expiry, email))

        conn.commit()
        cur.close()
        conn.close()

        reset_link = url_for('reset_password', token=token, _external=True)
        
        try:
            send_email(
                email,
                "Reset Your Password - ShelfBuddy",
                f"Click this link to reset your password:\n{reset_link}\nExpires in 15 minutes."
            )
            flash("Password reset link sent to your email.", "success")
        except Exception as e:
            print("RESET EMAIL ERROR:", str(e))
            flash("Couldn't send reset email right now. Please try again later.", "error")

        return redirect(url_for('login'))

    return render_template("forgot_password.html")

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    cur = conn.cursor()

    user = cur.execute("""
        SELECT email, reset_token_expiry
        FROM users
        WHERE reset_token=?
    """, (token,)).fetchone()

    if not user:
        cur.close()
        conn.close()
        return "Invalid Token"

    email, expiry = user

    if not expiry:
        cur.close()
        conn.close()
        return "Token expired"

    expiry = datetime.fromisoformat(expiry)

    if datetime.now() > expiry:
        cur.close()
        conn.close()
        return "Token Expired"

    if request.method == 'POST':
        new_password = request.form['password'].strip()

        if len(new_password) < 6:
            cur.close()
            conn.close()
            flash("Password must be at least 6 characters.", "error")
            return render_template("reset_password.html")

        hashed_password = generate_password_hash(new_password)

        cur.execute("""
    UPDATE users
    SET password=?, reset_token=NULL, reset_token_expiry=NULL, is_verified=1
    WHERE email=?
""", (hashed_password, email))

        conn.commit()
        cur.close()
        conn.close()

        flash("Password updated successfully. Please login.", "success")
        return redirect(url_for('login'))

    cur.close()
    conn.close()
    return render_template("reset_password.html")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
