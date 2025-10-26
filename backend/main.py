from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re

app = FastAPI(title="Thai Government Lottery API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "lottery.db"

# Pydantic models
class LotteryResult(BaseModel):
    draw_date: str
    prize_type: str
    prize_number: str
    prize_amount: Optional[int] = None

class DrawPeriod(BaseModel):
    draw_date: str
    period: str

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create lottery results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lottery_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_date TEXT NOT NULL,
            period TEXT NOT NULL,
            prize_type TEXT NOT NULL,
            prize_number TEXT NOT NULL,
            prize_amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(draw_date, period, prize_type, prize_number)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_draw_date ON lottery_results(draw_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_period ON lottery_results(period)
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def root():
    return {
        "message": "🎰 Thai Government Lottery API",
        "endpoints": {
            "/results": "Get all lottery results",
            "/results/{period}": "Get results for specific period (งวด)",
            "/periods": "Get all available periods",
            "/scrape": "Scrape latest results from GLO website",
            "/add": "Add lottery result manually"
        }
    }

@app.get("/results")
def get_all_results(limit: int = 100):
    """Get all lottery results with optional limit"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM lottery_results 
        ORDER BY draw_date DESC, id DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/results/{period}")
def get_results_by_period(period: str):
    """Get lottery results for a specific period (งวด)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM lottery_results 
        WHERE period = ? 
        ORDER BY 
            CASE prize_type
                WHEN 'รางวัลที่ 1' THEN 1
                WHEN 'เลขหน้า 3 ตัว' THEN 2
                WHEN 'เลขท้าย 3 ตัว' THEN 3
                WHEN 'เลขท้าย 2 ตัว' THEN 4
                ELSE 5
            END,
            id
    """, (period,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"No results found for period {period}")
    
    return [dict(row) for row in rows]

@app.get("/periods")
def get_all_periods():
    """Get all available lottery periods"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT period, draw_date 
        FROM lottery_results 
        ORDER BY draw_date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"period": row["period"], "draw_date": row["draw_date"]} for row in rows]

@app.post("/add")
def add_result(result: LotteryResult):
    """Add a lottery result manually"""
    # Extract period from date (format: งวดวันที่ 16 ตุลาคม 2567)
    period = f"งวดวันที่ {result.draw_date}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO lottery_results 
            (draw_date, period, prize_type, prize_number, prize_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (
            result.draw_date,
            period,
            result.prize_type,
            result.prize_number,
            result.prize_amount
        ))
        conn.commit()
        result_id = cursor.lastrowid
        conn.close()
        
        return {
            "message": "✅ Lottery result added successfully!",
            "id": result_id,
            "period": period
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="This result already exists in the database"
        )

@app.post("/add_bulk")
def add_bulk_results(results: List[LotteryResult]):
    """Add multiple lottery results at once"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    added_count = 0
    skipped_count = 0
    
    for result in results:
        period = f"งวดวันที่ {result.draw_date}"
        try:
            cursor.execute("""
                INSERT INTO lottery_results 
                (draw_date, period, prize_type, prize_number, prize_amount)
                VALUES (?, ?, ?, ?, ?)
            """, (
                result.draw_date,
                period,
                result.prize_type,
                result.prize_number,
                result.prize_amount
            ))
            added_count += 1
        except sqlite3.IntegrityError:
            skipped_count += 1
            continue
    
    conn.commit()
    conn.close()
    
    return {
        "message": f"✅ Bulk import completed!",
        "added": added_count,
        "skipped": skipped_count
    }

@app.get("/scrape")
async def scrape_latest_results():
    """
    Scrape latest lottery results from GLO website
    Note: This is a template - the actual implementation depends on the website structure
    """
    try:
        url = "https://www.glo.or.th/home-page"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch data from GLO website: {response.status_code}"
            )
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # This is a template - you'll need to inspect the actual HTML structure
        # and update these selectors accordingly
        results = []
        
        # Example parsing logic (needs to be adjusted based on actual HTML)
        # Look for lottery results containers
        result_containers = soup.find_all('div', class_='lottery-result')
        
        for container in result_containers:
            draw_date = container.find('span', class_='draw-date')
            prize_type = container.find('span', class_='prize-type')
            prize_number = container.find('span', class_='prize-number')
            
            if draw_date and prize_type and prize_number:
                results.append({
                    "draw_date": draw_date.text.strip(),
                    "prize_type": prize_type.text.strip(),
                    "prize_number": prize_number.text.strip()
                })
        
        if not results:
            return {
                "message": "⚠️ No results found. The website structure may have changed.",
                "html_preview": str(soup)[:500] + "...",
                "note": "Please inspect the HTML and update the scraper logic"
            }
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        added = 0
        
        for result in results:
            period = f"งวดวันที่ {result['draw_date']}"
            try:
                cursor.execute("""
                    INSERT INTO lottery_results 
                    (draw_date, period, prize_type, prize_number)
                    VALUES (?, ?, ?, ?)
                """, (
                    result['draw_date'],
                    period,
                    result['prize_type'],
                    result['prize_number']
                ))
                added += 1
            except sqlite3.IntegrityError:
                continue
        
        conn.commit()
        conn.close()
        
        return {
            "message": "✅ Scraping completed!",
            "total_found": len(results),
            "added_to_db": added
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping website: {str(e)}"
        )

@app.delete("/results/{result_id}")
def delete_result(result_id: int):
    """Delete a specific lottery result"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lottery_results WHERE id = ?", (result_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Result not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "✅ Result deleted successfully!"}

@app.get("/stats")
def get_statistics():
    """Get database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(DISTINCT period) as total_periods FROM lottery_results")
    total_periods = cursor.fetchone()["total_periods"]
    
    cursor.execute("SELECT COUNT(*) as total_results FROM lottery_results")
    total_results = cursor.fetchone()["total_results"]
    
    cursor.execute("""
        SELECT draw_date, period 
        FROM lottery_results 
        ORDER BY draw_date DESC 
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    conn.close()
    
    return {
        "total_periods": total_periods,
        "total_results": total_results,
        "latest_period": dict(latest) if latest else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)