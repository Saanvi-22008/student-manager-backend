import os
import json
from database import get_connection
import face_recognition

PHOTO_FOLDER = "photos"

def encode_and_update():
    conn = get_connection()

    for filename in os.listdir(PHOTO_FOLDER):
        rollno = os.path.splitext(filename)[0]
        filepath = os.path.join(PHOTO_FOLDER, filename)

        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            print(f"⚠️  No face found in {filename}, skipping")
            continue

        encoding_str = json.dumps(encodings[0].tolist())

        result = conn.execute(
            "UPDATE students SET face_encoding = ?, photo_path = ? WHERE rollno = ?",
            (encoding_str, filepath, rollno)
        )

        if result.rowcount == 0:
            print(f"⚠️  No student with rollno {rollno} found, skipping")
        else:
            print(f"✅ Updated rollno {rollno}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    encode_and_update()