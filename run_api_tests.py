"""
Automated End-to-End API Runner for RabbitLens FastAPI Backend.
Tests every endpoint sequentially (Auth -> Rabbits -> Scans -> Media -> Cascade Delete).

Usage:
    python run_api_tests.py [base_url]
    (Default base_url: http://localhost:8000)
"""

import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else os.getenv("API_BASE_URL", "http://localhost:8000")


def get_sample_jpeg_bytes() -> bytes:
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_paw.jpg")
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            return f.read()
    # Minimal valid 1x1 JPEG fallback
    return bytes.fromhex(
        "ffd8ffe000104a46494600010101004800480000ffdb004300030202020202030202020303030304"
        "060404040404080606050609080a0a090809090a0c0f0c0a0b0e0b09090d110d0e0f101011100a0c"
        "12131210130f101010ffc9000b080001000101011100ffcc000600101005ffda0008010100003f00"
        "d2cf20ffd9"
    )


def build_multipart_form_data(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = f"----RabbitLensRunnerBoundary{uuid.uuid4().hex}"
    buffer = io.BytesIO()

    for key, value in fields.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        buffer.write(f"{value}\r\n".encode("utf-8"))

    for key, (filename, file_bytes, content_type) in files.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        buffer.write(file_bytes)
        buffer.write(b"\r\n")

    buffer.write(f"--{boundary}--\r\n".encode("utf-8"))
    return buffer.getvalue(), f"multipart/form-data; boundary={boundary}"


def request(
    method: str,
    path: str,
    token: str | None = None,
    json_body: dict | None = None,
    form_urlencoded: dict | None = None,
    multipart: tuple[dict, dict] | None = None,
) -> tuple[int, dict | bytes, dict]:
    url = f"{BASE_URL}{path}"
    headers = {}
    data = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form_urlencoded is not None:
        data = urllib.parse.urlencode(form_urlencoded).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif multipart is not None:
        fields, files = multipart
        data, content_type = build_multipart_form_data(fields, files)
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            resp_headers = dict(resp.info())
            ctype = resp_headers.get("Content-Type", resp_headers.get("content-type", ""))
            if "application/json" in ctype:
                return resp.status, json.loads(raw.decode("utf-8")), resp_headers
            return resp.status, raw, resp_headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            parsed = {"raw": raw.decode("utf-8", errors="ignore")}
        return e.code, parsed, dict(e.headers)


def run_suite():
    print(f"============================================================")
    print(f" RabbitLens API Endpoint Runner -> {BASE_URL}")
    print(f"============================================================")

    passed = 0
    failed = 0

    def check(step_name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {step_name}")
        else:
            failed += 1
            print(f"  [FAIL] {step_name} -> {detail}")

    ts = int(time.time() * 1000)
    email = f"runner_{ts}@example.com"
    username = f"runner_{ts}"
    password = "Password123!"
    new_password = "NewPassword456!"
    jpeg_bytes = get_sample_jpeg_bytes()

    # 1. Health Check
    status, body, _ = request("GET", "/")
    check("01. GET / (Health Check)", status == 200 and isinstance(body, dict) and body.get("message") == "Hello World", f"status={status}, body={body}")

    # 2. Signup
    status, body, _ = request("POST", "/auth/signup", json_body={"email": email, "username": username, "password": password})
    check("02. POST /auth/signup", status == 200 and isinstance(body, dict) and body.get("email") == email, f"status={status}, body={body}")

    # 3. Login
    status, body, _ = request("POST", "/auth/login", form_urlencoded={"username": email, "password": password})
    access_token = body.get("access_token") if isinstance(body, dict) else None
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    check("03. POST /auth/login", status == 200 and bool(access_token) and bool(refresh_token), f"status={status}, body={body}")

    if not access_token:
        print("\nCannot proceed without access_token. Exiting.")
        sys.exit(1)

    # 4. Refresh Token
    status, body, _ = request("POST", "/auth/refresh", json_body={"refresh_token": refresh_token})
    if status == 200 and isinstance(body, dict):
        access_token = body.get("access_token", access_token)
        refresh_token = body.get("refresh_token", refresh_token)
    check("04. POST /auth/refresh", status == 200 and isinstance(body, dict) and "access_token" in body, f"status={status}, body={body}")

    # 5. Get Current User
    status, body, _ = request("GET", "/auth/me", token=access_token)
    check("05. GET /auth/me", status == 200 and isinstance(body, dict) and body.get("email") == email, f"status={status}, body={body}")

    # 6. Update Username
    updated_username = f"{username}_edited"
    status, body, _ = request("PUT", "/auth/me", token=access_token, json_body={"username": updated_username})
    check("06. PUT /auth/me (Update Username)", status == 200 and isinstance(body, dict) and body.get("username") == updated_username, f"status={status}, body={body}")

    # 7. Change Password
    status, body, _ = request(
        "PUT",
        "/auth/me/password",
        token=access_token,
        json_body={"current_password": password, "new_password": new_password},
    )
    check("07. PUT /auth/me/password", status == 200 and isinstance(body, dict) and "successfully" in body.get("message", ""), f"status={status}, body={body}")

    # 8. Create Rabbit
    status, body, _ = request(
        "POST",
        "/rabbits/",
        token=access_token,
        json_body={"name": "Fluffy", "date_of_birth": "2024-05-15", "breed": "Holland Lop"},
    )
    rabbit_id = body.get("id") if isinstance(body, dict) else None
    check("08. POST /rabbits/ (Create Rabbit)", status == 200 and bool(rabbit_id), f"status={status}, body={body}")

    # 9. Get All Rabbits
    status, body, _ = request("GET", "/rabbits/", token=access_token)
    check(
        "09. GET /rabbits/ (List Rabbits)",
        status == 200 and isinstance(body, list) and any(r.get("id") == rabbit_id for r in body),
        f"status={status}, body={body}",
    )

    # 10. Get Rabbit Details
    status, body, _ = request("GET", f"/rabbits/{rabbit_id}", token=access_token)
    check("10. GET /rabbits/{rabbit_id}", status == 200 and isinstance(body, dict) and body.get("id") == rabbit_id, f"status={status}, body={body}")

    # 11. Update Rabbit
    status, body, _ = request(
        "PUT",
        f"/rabbits/{rabbit_id}",
        token=access_token,
        json_body={"name": "Fluffy Updated", "date_of_birth": "2024-05-15", "breed": "Mini Lop"},
    )
    check(
        "11. PUT /rabbits/{rabbit_id} (Update Rabbit)",
        status == 200 and isinstance(body, dict) and body.get("name") == "Fluffy Updated",
        f"status={status}, body={body}",
    )

    # 12. Upload Rabbit Profile Photo
    status, body, _ = request(
        "POST",
        f"/rabbits/{rabbit_id}/photo",
        token=access_token,
        multipart=({}, {"file": ("test_paw.jpg", jpeg_bytes, "image/jpeg")}),
    )
    avatar_url = body.get("image_url") if isinstance(body, dict) else None
    check("12. POST /rabbits/{rabbit_id}/photo", status == 200 and bool(avatar_url), f"status={status}, body={body}")

    # 13. Process Paw Scan (back_left)
    status, body, _ = request(
        "POST",
        "/scans/",
        token=access_token,
        multipart=(
            {"rabbit_id": str(rabbit_id), "limb": "back_left", "mock_grade": "2"},
            {"file": ("test_paw.jpg", jpeg_bytes, "image/jpeg")},
        ),
    )
    photo_id = body.get("photo_id") if isinstance(body, dict) else None
    scan_media_url = body.get("image_url") if isinstance(body, dict) else None
    check(
        "13. POST /scans/ (back_left, mock_grade=2)",
        status == 200 and bool(photo_id) and body.get("classification") == 2,
        f"status={status}, body={body}",
    )

    # 14. Process Paw Scan (back_right)
    status, body, _ = request(
        "POST",
        "/scans/",
        token=access_token,
        multipart=(
            {"rabbit_id": str(rabbit_id), "limb": "back_right", "mock_grade": "1"},
            {"file": ("test_paw.jpg", jpeg_bytes, "image/jpeg")},
        ),
    )
    check(
        "14. POST /scans/ (back_right, mock_grade=1)",
        status == 200 and isinstance(body, dict) and body.get("limb") == "back_right" and body.get("classification") == 1,
        f"status={status}, body={body}",
    )

    # 15. Get Single Scan Result
    status, body, _ = request("GET", f"/scans/{photo_id}", token=access_token)
    check("15. GET /scans/{photo_id}", status == 200 and isinstance(body, dict) and body.get("photo_id") == photo_id, f"status={status}, body={body}")

    # 16. Get All Scans for Rabbit
    status, body, _ = request("GET", f"/scans/rabbit/{rabbit_id}", token=access_token)
    check("16. GET /scans/rabbit/{rabbit_id}", status == 200 and isinstance(body, list) and len(body) == 2, f"status={status}, body={body}")

    # 17. Stream Media File from MinIO
    if scan_media_url:
        status, body, headers = request("GET", scan_media_url)
        ctype = headers.get("Content-Type", headers.get("content-type", ""))
        check("17. GET /media/{file_path} (MinIO Stream)", status == 200 and "image" in ctype, f"status={status}, content-type={ctype}")

    # 18. Upload File Test
    status, body, _ = request(
        "POST",
        "/uploadfile/",
        token=access_token,
        multipart=({}, {"file": ("test_paw.jpg", jpeg_bytes, "image/jpeg")}),
    )
    check("18. POST /uploadfile/", status == 200 and isinstance(body, dict) and body.get("filename") == "test_paw.jpg", f"status={status}, body={body}")

    # 19. Delete Rabbit (Cascade Delete Photos & DetectionResults)
    status, body, _ = request("DELETE", f"/rabbits/{rabbit_id}", token=access_token)
    check(
        "19. DELETE /rabbits/{rabbit_id} (Cascade Delete)",
        status == 200 and isinstance(body, dict) and "deleted successfully" in body.get("message", ""),
        f"status={status}, body={body}",
    )

    # 20. Verify Rabbit Deleted (Expect 404)
    status, body, _ = request("GET", f"/rabbits/{rabbit_id}", token=access_token)
    check("20. GET /rabbits/{rabbit_id} after delete (Expect 404)", status == 404, f"status={status}, body={body}")

    # 21. Verify Scan Photo Cascade Deleted (Expect 404)
    status, body, _ = request("GET", f"/scans/{photo_id}", token=access_token)
    check("21. GET /scans/{photo_id} after rabbit delete (Expect 404)", status == 404, f"status={status}, body={body}")

    print(f"============================================================")
    print(f" Summary: {passed} passed, {failed} failed (Total: {passed + failed})")
    print(f"============================================================")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_suite()
