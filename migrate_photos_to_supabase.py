"""One-off migration: upload the committed photos/ files to Supabase Storage and
point each student's photo_path at the new public URL.

Existing rows were seeded with local-disk paths like "photos/1.jpg". After the
switch to Supabase Storage those paths no longer resolve, so this backfills them.
New students added through the API already store Supabase URLs and don't need this.

Run once, locally, after the Supabase env vars are set:
    python migrate_photos_to_supabase.py
"""

import os
import glob
from database import get_connection
from storage import ensure_bucket, upload_photo

ensure_bucket()

conn = get_connection()
rows = conn.execute("SELECT rollno, photo_path FROM students").fetchall()

updated = 0
for r in rows:
    rollno = r["rollno"]
    matches = glob.glob(os.path.join("photos", f"{rollno}.*"))
    if not matches:
        continue
    with open(matches[0], "rb") as f:
        data = f.read()
    ext = matches[0].rsplit(".", 1)[-1].lower()
    ctype = "image/png" if ext == "png" else "image/jpeg"
    url = upload_photo(f"{rollno}.jpg", data, ctype)
    conn.execute("UPDATE students SET photo_path = %s WHERE rollno = %s", (url, rollno))
    conn.commit()
    updated += 1
    print(f"rollno {rollno} -> {url}")

conn.close()
print(f"Done. Updated {updated} student photo(s).")
