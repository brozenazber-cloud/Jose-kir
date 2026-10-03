import sqlite3
import os

DB_FILE = "shop.db"


def connect():
    return sqlite3.connect(DB_FILE)


def init():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            stock TEXT DEFAULT 'آماده',
            featured INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS discounts (
            code TEXT PRIMARY KEY,
            percent INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            used INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            price INTEGER,
            discount INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute("""
            INSERT INTO products
            (name, description, price, stock, featured)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "VIP",
            "دسترسی ویژه و امکانات VIP",
            100000,
            "آماده",
            1
        ))

        cur.execute("""
            INSERT INTO products
            (name, description, price, stock, featured)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "LEGEND",
            "پکیج ویژه LEGEND",
            200000,
            "آماده",
            1
        ))

    conn.commit()
    conn.close()


def create_user(user_id, username="", first_name=""):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,)
    )

    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO users
            (id, username, first_name)
            VALUES (?, ?, ?)
        """, (
            user_id,
            username,
            first_name
        ))
    else:
        cur.execute("""
            UPDATE users
            SET username = ?, first_name = ?
            WHERE id = ?
        """, (
            username,
            first_name,
            user_id
        ))

    conn.commit()
    conn.close()


def get_balance(user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    conn.close()

    return row[0] if row else 0


def add_balance(user_id, amount):
    conn = connect()

    conn.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE id = ?
    """, (
        amount,
        user_id
    ))

    conn.commit()
    conn.close()


def get_products():
    conn = connect()

    cur = conn.execute("""
        SELECT *
        FROM products
        ORDER BY featured DESC, id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return rows


def get_product(product_id):
    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (
        product_id,
    )).fetchone()

    conn.close()

    return row


def add_product(name, description, price, stock="آماده", featured=0):
    conn = connect()

    conn.execute("""
        INSERT INTO products
        (name, description, price, stock, featured)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        description,
        price,
        stock,
        featured
    ))

    conn.commit()
    conn.close()


def add_discount(code, percent):
    conn = connect()

    conn.execute("""
        INSERT OR REPLACE INTO discounts
        (code, percent, active, used)
        VALUES (?, ?, 1, 0)
    """, (
        code.upper(),
        percent
    ))

    conn.commit()
    conn.close()


def get_discount(code):
    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM discounts
        WHERE code = ?
        AND active = 1
    """, (
        code.upper(),
    )).fetchone()

    conn.close()

    return row


def create_topup(user_id, amount, receipt):
    conn = connect()

    cur = conn.execute("""
        INSERT INTO topups
        (user_id, amount, receipt)
        VALUES (?, ?, ?)
    """, (
        user_id,
        amount,
        receipt
    ))

    topup_id = cur.lastrowid

    conn.commit()
    conn.close()

    return topup_id


def get_pending_topups():
    conn = connect()

    rows = conn.execute("""
        SELECT *
        FROM topups
        WHERE status = 'pending'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return rows


def approve_topup(topup_id):
    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM topups
        WHERE id = ?
        AND status = 'pending'
    """, (
        topup_id,
    )).fetchone()

    if not row:
        conn.close()
        return None

    conn.execute("""
        UPDATE topups
        SET status = 'approved'
        WHERE id = ?
    """, (
        topup_id,
    ))

    conn.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE id = ?
    """, (
        row[2],
        row[1]
    ))

    conn.commit()
    conn.close()

    return row


def reject_topup(topup_id):
    conn = connect()

    row = conn.execute("""
        SELECT *
        FROM topups
        WHERE id = ?
        AND status = 'pending'
    """, (
        topup_id,
    )).fetchone()

    if not row:
        conn.close()
        return None

    conn.execute("""
        UPDATE topups
        SET status = 'rejected'
        WHERE id = ?
    """, (
        topup_id,
    ))

    conn.commit()
    conn.close()

    return row


def buy_product(user_id, product_id, discount_code=None):
    conn = connect()

    user = conn.execute("""
        SELECT balance
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (
        product_id,
    )).fetchone()

    if not user:
        conn.close()
        return False, "کاربر پیدا نشد."

    if not product:
        conn.close()
        return False, "محصول پیدا نشد."

    original_price = product[3]
    final_price = original_price
    discount_amount = 0

    discount = None

    if discount_code:
        discount = conn.execute("""
            SELECT *
            FROM discounts
            WHERE code = ?
            AND active = 1
        """, (
            discount_code.upper(),
        )).fetchone()

    if discount:
        discount_amount = int(
            original_price * discount[1] / 100
        )

        final_price = max(
            0,
            original_price - discount_amount
        )

    if user[0] < final_price:
        conn.close()
        return False, "موجودی کافی نیست."

    conn.execute("""
        UPDATE users
        SET balance = balance - ?
        WHERE id = ?
    """, (
        final_price,
        user_id
    ))

    conn.execute("""
        INSERT INTO orders
        (user_id, product_id, price, discount)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        product_id,
        final_price,
        discount_amount
    ))

    if discount:
        conn.execute("""
            UPDATE discounts
            SET used = used + 1
            WHERE code = ?
        """, (
            discount_code.upper(),
        ))

    conn.commit()
    conn.close()

    return True, {
        "name": product[1],
        "price": final_price,
        "discount": discount_amount
    }


init()
