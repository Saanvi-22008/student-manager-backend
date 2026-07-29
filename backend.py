from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_connection, init_db, seed_db
from groq import Groq
from flask import send_from_directory
import json
import face_recognition
import os
from dotenv import load_dotenv
load_dotenv()

PHOTO_FOLDER= "photos"
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__)
CORS(app)

@app.route('/photos/<filename>')
def get_photo(filename):
    return send_from_directory(PHOTO_FOLDER, filename)

@app.route("/api/ai", methods=["POST"])
@app.route("/api/ai", methods=["POST"])
def ask_ai():
    data = request.get_json()
    question = data["prompt"]

    conn = get_connection()
    students = conn.execute("SELECT * FROM students").fetchall()
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
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    result = []
    for s in students:
        d = dict(s)
        if d.get('photo_path'):
            filename = os.path.basename(d['photo_path'])  # extracts just "7.jpg" from "photos/7.jpg"
            d['photo_url'] = f"/photos/{filename}"
        else:
            d['photo_url'] = None
        result.append(d)

    return jsonify(result)

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
    all_students = conn.execute("SELECT * FROM students").fetchall()
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
        photo_path = os.path.join(PHOTO_FOLDER, f"{rollno}.jpg")
        photo.save(photo_path)

        image = face_recognition.load_image_file(photo_path)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) == 0:
            os.remove(photo_path)
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
                os.remove(photo_path)
                return jsonify({
                    "error": f"Person already exists in the database as {student['name']} (Roll {student['rollno']})"
                })
        # --- end duplicate check ---

        encoding_str = json.dumps(new_encoding.tolist())
        photo_path_value = photo_path

    conn = get_connection()
    conn.execute(
        "INSERT INTO students (rollno, name, grade, marks, face_encoding, photo_path) VALUES (?, ?, ?, ?, ?, ?)",
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
    student = conn.execute("SELECT * FROM students WHERE rollno = ?", (rollno,)).fetchone()

    if not student:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    # --- delete the old photo file first (Task 3) ---
    old_path = student['photo_path']
    if old_path and os.path.exists(old_path):
        os.remove(old_path)
    # --- end delete old photo ---

    new_path = os.path.join(PHOTO_FOLDER, f"{rollno}.jpg")
    photo.save(new_path)

    image = face_recognition.load_image_file(new_path)
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        os.remove(new_path)
        conn.close()
        return jsonify({"error": "No face detected in photo"}), 400

    encoding_str = json.dumps(encodings[0].tolist())

    conn.execute(
        "UPDATE students SET face_encoding = ?, photo_path = ? WHERE rollno = ?",
        (encoding_str, new_path, rollno)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Photo updated"})

def add_photo_urls(students):
    result = []
    for s in students:
        d = dict(s)
        if d.get('photo_path') and os.path.exists(d['photo_path']):
            filename = os.path.basename(d['photo_path'])
            d['photo_url'] = f"/photos/{filename}"
        else:
            d['photo_url'] = None
        result.append(d)
    return result

@app.route("/api/students/search", methods=["GET"])
def search_students():
    name = request.args.get("name", "")
    conn = get_connection()
    students = conn.execute(
        "SELECT * FROM students WHERE name LIKE ?", (f"%{name}%",)
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
    avg = conn.execute("SELECT AVG(marks) FROM students").fetchone()[0]
    students = conn.execute(
        "SELECT * FROM students WHERE marks > ?", (avg,)
    ).fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route("/api/students/below-avg", methods=["GET"])
def get_below_avg():
    conn = get_connection()
    avg = conn.execute("SELECT AVG(marks) FROM students").fetchone()[0]
    students = conn.execute(
        "SELECT * FROM students WHERE marks < ?", (avg,)
    ).fetchall()
    conn.close()
    return jsonify(add_photo_urls(students))

@app.route("/api/students/<int:rollno>", methods=["DELETE"])
def delete_student(rollno):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE rollno = ?", (rollno,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})

if __name__ == "__main__":
    init_db()
    seed_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)