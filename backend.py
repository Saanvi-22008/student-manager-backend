from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_connection, init_db, seed_db
from groq import Groq
import io
import json
import face_recognition
import os
from dotenv import load_dotenv
from storage import upload_photo, delete_photo
load_dotenv()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__)
CORS(app)

@app.route("/api/ai", methods=["POST"])
@app.route("/api/ai", methods=["POST"])
def ask_ai():
    data = request.get_json()
    question = data["prompt"]

    conn = get_connection()
    students = conn.execute("SELECT * FROM students ORDER BY rollno").fetchall()
    conn.close()

    # Strip out face_encoding — irrelevant and confusing for text questions
    students_list = [
        {k: v for k, v in dict(s).items() if k != "face_encoding"}
        for s in students
    ]

    prompt = f"""
    You are a classroom assistant. Here is the student data:
    {students_list}
    Answer this question based on the data: {question}
    Answer in 20 words or fewer.
    """

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return jsonify({"answer": response.choices[0].message.content})

@app.route("/api/students", methods=["GET"])
def get_students():
    conn = get_connection()
    students = conn.execute("SELECT * FROM students ORDER BY rollno").fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route('/api/search_by_photo', methods=['POST'])
def search_by_photo():
    photo = request.files.get('photo')
    question = request.form.get('question', '')  # e.g. "is this the topper?"

    if not photo:
        return jsonify({"error": "No photo uploaded"})

    image = face_recognition.load_image_file(photo)
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return jsonify({"error": "No face detected in photo"})

    query_encoding = encodings[0]

    conn = get_connection()
    students = conn.execute("SELECT * FROM students WHERE face_encoding IS NOT NULL").fetchall()
    conn.close()

    matched_student = None
    for student in students:
        known_encoding = json.loads(student['face_encoding'])
        match = face_recognition.compare_faces([known_encoding], query_encoding, tolerance=0.5)
        if match[0]:
            matched_student = student
            break

    if not matched_student:
        return jsonify({"message": "No matching student found"})

    # basic version: just identify the student
    result = {
        "rollno": matched_student['rollno'],
        "name": matched_student['name'],
        "grade": matched_student['grade'],
        "marks": matched_student['marks']
    }

    # If no question was typed, just return who it is
    if not question.strip():
        return jsonify(result)

    # question-answer section
    conn = get_connection()
    all_students = conn.execute("SELECT * FROM students ORDER BY rollno").fetchall()
    conn.close()
    students_list = [
        {k: v for k, v in dict(s).items() if k != "face_encoding"}
        for s in all_students
    ]

    prompt = f"""
        You are a classroom assistant. Here is the student data:
        {students_list}
        The uploaded photo was identified as: {result['name']} (Roll {result['rollno']}, Marks {result['marks']}).
        Answer this question about this specific student: {question}
        Answer in 20 words or fewer.
        """

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return jsonify({"student": result, "answer": response.choices[0].message.content})

@app.route('/api/add_student', methods=['POST'])
def add_student():
    rollno = request.form['rollno']
    name = request.form['name']
    grade = request.form['grade']
    marks = request.form['marks']
    photo = request.files.get('photo')

    encoding_str = None
    photo_path_value = None

    if photo:
        file_bytes = photo.read()

        image = face_recognition.load_image_file(io.BytesIO(file_bytes))
        encodings = face_recognition.face_encodings(image)
        if len(encodings) == 0:
            return jsonify({"error": "No face detected in photo"})

        new_encoding = encodings[0]

        # --- check for duplicate person before inserting ---
        conn = get_connection()
        existing_students = conn.execute(
            "SELECT * FROM students WHERE face_encoding IS NOT NULL"
        ).fetchall()
        conn.close()

        for student in existing_students:
            known_encoding = json.loads(student['face_encoding'])
            match = face_recognition.compare_faces([known_encoding], new_encoding, tolerance=0.5)
            if match[0]:
                return jsonify({
                    "error": f"Person already exists in the database as {student['name']} (Roll {student['rollno']})"
                })
        # --- end duplicate check ---

        encoding_str = json.dumps(new_encoding.tolist())
        # Upload to Supabase Storage only after passing face + duplicate checks
        photo_path_value = upload_photo(f"{rollno}.jpg", file_bytes, photo.mimetype or "image/jpeg")

    conn = get_connection()
    conn.execute(
        "INSERT INTO students (rollno, name, grade, marks, face_encoding, photo_path) VALUES (%s, %s, %s, %s, %s, %s)",
        (rollno, name, grade, marks, encoding_str, photo_path_value)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Student added"})

@app.route('/api/update_photo/<int:rollno>', methods=['POST'])
def update_photo(rollno):
    photo = request.files.get('photo')
    if not photo:
        return jsonify({"error": "No photo uploaded"}), 400

    conn = get_connection()
    student = conn.execute("SELECT * FROM students WHERE rollno = %s", (rollno,)).fetchone()

    if not student:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    old_url = student['photo_path']

    file_bytes = photo.read()
    image = face_recognition.load_image_file(io.BytesIO(file_bytes))
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        conn.close()
        return jsonify({"error": "No face detected in photo"}), 400

    encoding_str = json.dumps(encodings[0].tolist())

    # Upload new photo (overwrites <rollno>.jpg in the bucket)
    new_url = upload_photo(f"{rollno}.jpg", file_bytes, photo.mimetype or "image/jpeg")

    # Remove the old object if it lived under a different key (best-effort)
    if old_url and old_url != new_url:
        delete_photo(old_url)

    conn.execute(
        "UPDATE students SET face_encoding = %s, photo_path = %s WHERE rollno = %s",
        (encoding_str, new_url, rollno)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Photo updated"})

def add_photo_urls(students):
    # photo_path now holds the full Supabase Storage public URL, so photo_url is
    # simply that value (single source of truth — no filename guessing).
    result = []
    for s in students:
        d = dict(s)
        d['photo_url'] = d.get('photo_path') or None
        result.append(d)
    return result

@app.route("/api/students/search", methods=["GET"])
def search_students():
    name = request.args.get("name", "")
    conn = get_connection()
    students = conn.execute(
        "SELECT * FROM students WHERE name LIKE %s ORDER BY rollno", (f"%{name}%",)
    ).fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route("/api/students/topper", methods=["GET"])
def get_topper():
    conn = get_connection()
    student = conn.execute(
        "SELECT * FROM students ORDER BY marks DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if student:
        return jsonify(add_photo_urls([student]))
    return jsonify([])

@app.route("/api/students/above-avg", methods=["GET"])
def get_above_avg():
    conn = get_connection()
    avg = conn.execute("SELECT AVG(marks) AS avg FROM students").fetchone()['avg']
    students = conn.execute(
        "SELECT * FROM students WHERE marks > %s ORDER BY rollno", (avg,)
    ).fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route("/api/students/below-avg", methods=["GET"])
def get_below_avg():
    conn = get_connection()
    avg = conn.execute("SELECT AVG(marks) AS avg FROM students").fetchone()['avg']
    students = conn.execute(
        "SELECT * FROM students WHERE marks < %s ORDER BY rollno", (avg,)
    ).fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route("/api/students/<int:rollno>", methods=["DELETE"])
def delete_student(rollno):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE rollno = %s", (rollno,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    init_db()
    seed_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)