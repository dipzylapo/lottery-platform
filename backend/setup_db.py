import sqlite3

def create_tables():
    conn = sqlite3.connect("lottery.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lottery_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_date TEXT NOT NULL,
        prize_name TEXT NOT NULL,
        prize_number TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database and table created successfully!")

if __name__ == "__main__":
    create_tables()
