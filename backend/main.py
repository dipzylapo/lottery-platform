from fastapi import FastAPI
import sqlite3
from typing import List, Dict

app = FastAPI(title="Lottery Results API")

DB_PATH = "lottery.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def root():
    return {"message": "🎉 Lottery API is running!"}

@app.get("/results")
def get_results() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lottery_results ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/add")
def add_result(draw_date: str, prize_name: str, prize_number: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lottery_results (draw_date, prize_name, prize_number)
        VALUES (?, ?, ?)
    """, (draw_date, prize_name, prize_number))
    conn.commit()
    conn.close()
    return {"message": "✅ Result added successfully!"}
