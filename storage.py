"""Supabase Storage helper.

Uses only the Python standard library (urllib) so it adds NO new entries to
requirements.txt — this keeps the fragile dlib/face_recognition Render build
setup completely untouched.

Photos are uploaded to a Supabase Storage bucket and the resulting public URL
is stored in the students.photo_path column (same role that column already
played for the old local-disk path).
"""

import os
import json
import urllib.request
import urllib.error

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "photos")

_bucket_ready = False


def _headers(extra=None):
    h = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY or "",
    }
    if extra:
        h.update(extra)
    return h


def _request(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def ensure_bucket():
    """Create the bucket (public) if it's missing, or make it public if it exists."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return
    status, _ = _request(
        "GET", f"{SUPABASE_URL}/storage/v1/bucket/{SUPABASE_BUCKET}", headers=_headers()
    )
    if status == 404:
        body = json.dumps(
            {"id": SUPABASE_BUCKET, "name": SUPABASE_BUCKET, "public": True}
        ).encode()
        _request(
            "POST",
            f"{SUPABASE_URL}/storage/v1/bucket",
            data=body,
            headers=_headers({"Content-Type": "application/json"}),
        )
    else:
        _request(
            "PUT",
            f"{SUPABASE_URL}/storage/v1/bucket/{SUPABASE_BUCKET}",
            data=json.dumps({"public": True}).encode(),
            headers=_headers({"Content-Type": "application/json"}),
        )


def _ensure_bucket_once():
    global _bucket_ready
    if _bucket_ready:
        return
    try:
        ensure_bucket()
    except Exception as e:
        print("ensure_bucket skipped:", e)
    _bucket_ready = True


def public_url(path):
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path}"


def upload_photo(path, data, content_type="image/jpeg"):
    """Upload bytes to the bucket (upsert / overwrite). Returns the public URL."""
    _ensure_bucket_once()
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path}"
    status, resp = _request(
        "POST",
        url,
        data=data,
        headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
    )
    if status not in (200, 201):
        raise RuntimeError(f"Supabase upload failed ({status}): {resp[:200]!r}")
    return public_url(path)


def delete_photo(url_or_path):
    """Delete an object given its public URL or bucket path. Best-effort (never raises)."""
    if not url_or_path:
        return
    marker = f"/storage/v1/object/public/{SUPABASE_BUCKET}/"
    if marker in url_or_path:
        path = url_or_path.split(marker, 1)[1]
    elif url_or_path.startswith("http"):
        return  # unknown external URL — leave it alone
    else:
        path = os.path.basename(url_or_path)  # legacy local-style path e.g. "photos/7.jpg"
    try:
        _request(
            "DELETE",
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path}",
            headers=_headers(),
        )
    except Exception as e:
        print("delete_photo skipped:", e)
