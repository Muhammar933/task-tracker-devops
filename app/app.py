import os
import time
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "tasksdb"),
        user=os.environ.get("DB_USER", "tasks"),
        password=os.environ["DB_PASSWORD"],
    )


def query(sql, params=(), fetch=False):
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
    finally:
        conn.close()


def init_db():
    for _ in range(10):
        try:
            query(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
                """
            )
            return
        except psycopg2.OperationalError:
            print("Database ready nahi hai, dobara koshish...")
            time.sleep(2)
    raise RuntimeError("Database se connect nahi ho saka")


@app.get("/health")
def health():
    try:
        query("SELECT 1")
        return jsonify(status="ok")
    except Exception:
        return jsonify(status="db_down"), 503


@app.get("/tasks")
def list_tasks():
    rows = query("SELECT id, title, done FROM tasks ORDER BY id", fetch=True)
    return jsonify([{"id": r[0], "title": r[1], "done": r[2]} for r in rows])


@app.post("/tasks")
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title zaroori hai"), 400
    row = query(
        "INSERT INTO tasks (title) VALUES (%s) RETURNING id", (title,), fetch=True
    )
    return jsonify(id=row[0][0], title=title, done=False), 201


@app.put("/tasks/<int:task_id>/done")
def mark_done(task_id):
    row = query(
        "UPDATE tasks SET done = TRUE WHERE id = %s RETURNING id",
        (task_id,),
        fetch=True,
    )
    if not row:
        return jsonify(error="task nahi mila"), 404
    return jsonify(id=task_id, done=True)


@app.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    row = query("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,), fetch=True)
    if not row:
        return jsonify(error="task nahi mila"), 404
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
