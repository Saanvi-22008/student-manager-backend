import face_recognition
from PIL import Image
import numpy as np

def load_and_convert(path):
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    arr = np.ascontiguousarray(arr)  # force contiguous memory layout
    return arr

image1 = load_and_convert("photos/1.jpg")
image2 = load_and_convert("saanvi2.jpg")

encoding1 = face_recognition.face_encodings(image1)[0]
encoding2 = face_recognition.face_encodings(image2)[0]

results = face_recognition.compare_faces([encoding1], encoding2)

print("Are these the same person?", results[0])