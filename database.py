import psycopg2
import psycopg2.extras
import csv
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            rollno  INTEGER PRIMARY KEY,
            name    TEXT NOT NULL,
            grade   TEXT NOT NULL,
            marks   INTEGER NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database ready!")

def seed_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    existing = cur.fetchone()[0]
    if existing > 0:
        print("Data already exists, skipping seed.")
        cur.close()
        conn.close()
        return

    with open("students.csv") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cur.execute(
                "INSERT INTO students (rollno, name, grade, marks) VALUES (%s, %s, %s, %s)",
                (row["rollno"], row["name"], row["grade"], int(row["marks"]))
            )

    conn.commit()
    cur.close()
    conn.close()
    print("Database seeded!")

def add_face_column():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE students ADD COLUMN face_encoding TEXT")
        conn.commit()
        print("Column added!")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("Column already exists, skipping.")
    cur.close()
    conn.close()

def add_photo_path_column():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE students ADD COLUMN photo_path TEXT")
        conn.commit()
        print("photo_path column added!")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("photo_path column already exists, skipping.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    add_face_column()
    add_photo_path_column()