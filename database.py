import sqlite3
import csv

DB_PATH = "students.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            rollno  INTEGER PRIMARY KEY,
            name    TEXT NOT NULL,
            grade   TEXT NOT NULL,
            marks   INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("Database ready!")

def seed_db():
    conn = get_connection()

    # Check if data already exists — if yes, skip
    existing = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if existing > 0:
        print("Data already exists, skipping seed.")
        conn.close()
        return

    # Read the CSV and insert each row
    with open("students.csv") as file:
        reader = csv.DictReader(file)  # reads each row as a dict like {"name": "Saanvi", "grade": "10", "marks": "92"}
        for row in reader:
            conn.execute(
                "INSERT INTO students (rollno, name, grade, marks) VALUES (?, ?, ?, ?)",
                (row["rollno"], row["name"], row["grade"], int(row["marks"]))
            )

    conn.commit()
    conn.close()
    print("Database seeded!")

def add_face_column():
    conn = get_connection()
    try:
        conn.execute("ALTER TABLE students ADD COLUMN face_encoding TEXT")
        conn.commit()
        print("Column added!")
    except sqlite3.OperationalError:
        print("Column already exists, skipping.")
    conn.close()

def add_photo_path_column():
    conn = get_connection()
    try:
        conn.execute("ALTER TABLE students ADD COLUMN photo_path TEXT")
        conn.commit()
        print("photo_path column added!")
    except sqlite3.OperationalError:
        print("photo_path column already exists, skipping.")
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    add_face_column()
    add_photo_path_column()