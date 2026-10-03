import sqlite3, os
from pathlib import Path
from datetime import datetime

DB = Path("data/shop.db")
DB.parent.mkdir(exist_ok=True)

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
      description TEXT DEFAULT '', price INTEGER NOT NULL,
      stock TEXT DEFAULT '', featured INTEGER DEFAULT 0, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS discounts(
      code TEXT PRIMARY KEY, percent INTEGER DEFAULT 0, amount INTEGER DEFAULT 0,
      uses_left INTEGER DEFAULT 1, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS topups(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
      receipt TEXT DEFAULT '', status TEXT DEFAULT 'pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER,
      price INTEGER, discount INTEGER DEFAULT 0, created_at TEXT NOT NULL
    );
    """)
    if c.execute("SELECT COUNT(*) n FROM products").fetchone()["n"] == 0:
        c.execute("INSERT INTO products(name,description,price,stock,featured) VALUES(?,?,?,?,?)",
                  ("کانفیگ VIP","کانفیگ ویژه با تحویل سریع",100000,"آماده",1))
        c.execute("INSERT INTO products(name,description,price,stock) VALUES(?,?,?,?)",
                  ("کانفیگ معمولی","کانفیگ اقتصادی سرور",50000,"آماده"))
    c.commit(); c.close()

def user(uid, username=""):
    c=conn(); c.execute("INSERT OR IGNORE INTO users(id,username,created_at) VALUES(?,?,?)",
                         (uid,username,datetime.now().isoformat()))
    if username: c.execute("UPDATE users SET username=? WHERE id=?", (username,uid))
    c.commit()
    r=c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); c.close(); return r

def products(active=True):
    c=conn()
    q="SELECT * FROM products" + (" WHERE active=1" if active else "") + " ORDER BY featured DESC,id DESC"
    r=c.execute(q).fetchall(); c.close(); return r

def product(pid):
    c=conn(); r=c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone(); c.close(); return r

def balance(uid):
    return user(uid)["balance"]

def change_balance(uid, amount):
    user(uid); c=conn(); c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount,uid)); c.commit(); c.close()

def add_topup(uid, amount, receipt):
    c=conn(); c.execute("INSERT INTO topups(user_id,amount,receipt,created_at) VALUES(?,?,?,?)",
                        (uid,amount,receipt,datetime.now().isoformat())); c.commit(); c.close()

def pending_topups():
    c=conn(); r=c.execute("SELECT * FROM topups WHERE status='pending' ORDER BY id DESC").fetchall(); c.close(); return r

def topup(tid, approve):
    c=conn(); r=c.execute("SELECT * FROM topups WHERE id=?", (tid,)).fetchone()
    if not r or r["status"]!="pending": c.close(); return None
    status="approved" if approve else "rejected"
    c.execute("UPDATE topups SET status=? WHERE id=?", (status,tid))
    if approve: c.execute("UPDATE users SET balance=balance+? WHERE id=?", (r["amount"],r["user_id"]))
    c.commit(); c.close(); return r

def add_product(name, desc, price, stock, featured=0):
    c=conn(); c.execute("INSERT INTO products(name,description,price,stock,featured) VALUES(?,?,?,?,?)",
                         (name,desc,price,stock,featured)); c.commit(); c.close()

def add_discount(code, percent, amount, uses):
    c=conn(); c.execute("INSERT OR REPLACE INTO discounts(code,percent,amount,uses_left,active) VALUES(?,?,?,?,1)",
                         (code.upper(),percent,amount,uses)); c.commit(); c.close()

def get_discount(code):
    c=conn(); r=c.execute("SELECT * FROM discounts WHERE code=? AND active=1 AND uses_left>0",
                          (code.upper(),)).fetchone(); c.close(); return r

def use_discount(code):
    c=conn(); c.execute("UPDATE discounts SET uses_left=uses_left-1 WHERE code=? AND uses_left>0",(code.upper(),)); c.commit(); c.close()

def buy(uid,pid,code=""):
    p=product(pid)
    if not p or not p["active"]: return False,"محصول پیدا نشد."
    price=p["price"]; discount=0; d=get_discount(code) if code else None
    if d:
        discount = d["amount"] if d["amount"] else int(price*d["percent"]/100)
        discount=min(discount,price); price-=discount
    if balance(uid)<price: return False,"موجودی کافی نیست."
    c=conn(); c.execute("UPDATE users SET balance=balance-? WHERE id=?", (price,uid))
    c.execute("INSERT INTO orders(user_id,product_id,price,discount,created_at) VALUES(?,?,?,?,?)",
              (uid,pid,price,discount,datetime.now().isoformat()))
    c.commit(); c.close()
    if d: use_discount(code)
    return True,(p,price)
