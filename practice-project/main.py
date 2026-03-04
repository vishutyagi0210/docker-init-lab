from flask import Flask, jsonify, request
import psycopg2
import redis
import os
import json
import time

app = Flask(__name__)

# ── Redis connection ──────────────────────────────────────────────────────────
cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True
)

# ── Postgres connection ───────────────────────────────────────────────────────
def get_password():
    secret_file = os.getenv("DB_PASSWORD_FILE")
    if secret_file:
        with open(secret_file, "r") as f:
            return f.read().strip()
    return os.getenv("DB_PASSWORD", "apppassword")

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "appdb"),
        user=os.getenv("DB_USER", "appuser"),
        password=get_password()
    )

# ── Init DB table on startup ──────────────────────────────────────────────────
def init_db():
    for attempt in range(10):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Database initialized!")
            return
        except Exception as e:
            print(f"⏳ Waiting for DB... attempt {attempt+1}/10 ({e})")
            time.sleep(3)
    raise RuntimeError("Could not connect to database after 10 attempts.")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return jsonify({
        "app": "Flask + Postgres + Redis Stack",
        "status": "running 🚀",
        "endpoints": {
            "GET  /messages":        "List all messages (cached)",
            "POST /messages":        "Create a new message  { \"text\": \"...\" }",
            "GET  /cache/ping":      "Test Redis connection",
            "GET  /db/ping":         "Test Postgres connection",
        }
    })


@app.route("/messages", methods=["GET"])
def get_messages():
    # Try cache first
    cached = cache.get("messages")
    if cached:
        return jsonify({"source": "cache 🟢", "messages": json.loads(cached)})

    # Hit DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, text, created_at::text FROM messages ORDER BY id DESC")
    rows = [{"id": r[0], "text": r[1], "created_at": r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()

    # Store in cache for 30 seconds
    cache.setex("messages", 30, json.dumps(rows))

    return jsonify({"source": "database 🐘", "messages": rows})


@app.route("/messages", methods=["POST"])
def create_message():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Field 'text' is required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (text) VALUES (%s) RETURNING id, text, created_at::text",
        (data["text"],)
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    # Bust cache so next GET is fresh
    cache.delete("messages")

    return jsonify({"id": row[0], "text": row[1], "created_at": row[2]}), 201


@app.route("/cache/ping")
def cache_ping():
    try:
        cache.ping()
        return jsonify({"redis": "ok ✅", "host": os.getenv("REDIS_HOST", "redis")})
    except Exception as e:
        return jsonify({"redis": "error ❌", "detail": str(e)}), 500


@app.route("/db/ping")
def db_ping():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"postgres": "ok ✅", "host": os.getenv("DB_HOST", "db")})
    except Exception as e:
        return jsonify({"postgres": "error ❌", "detail": str(e)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
