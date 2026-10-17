# Rabbit Backend (FastAPI)

This is the backend service for the Rabbit application, built with **FastAPI**, **PostgreSQL**, and **MinIO**. It includes JWT-based authentication, rabbit management, paw health check scans, local S3-compatible object storage for photo uploads, and integration with an Azure Machine Learning endpoint for inference.

## 🚀 Features

* **FastAPI Framework:** High-performance, modern Python web framework.
* **PostgreSQL Database:** Relational database running via Docker.
* **MinIO Object Storage:** S3-compatible high-performance object storage for storing rabbit avatars and paw scan photos.
* **JWT Authentication:** Secure user signup, login, and protected routes (`/auth`). Supports hybrid username/email login.
* **Rabbits Module:** Core business logic and API endpoints for managing rabbit profiles and avatars (`/rabbits`).
* **Scans Module:** Endpoints for uploading paw scan photos, generating mock/AI detection results, and querying scan history (`/scans`).
* **Media Streaming Proxy:** FastAPI endpoint (`/media/{file_path}`) that safely streams files from MinIO to mobile clients and emulators.
* **Azure ML Integration:** Communicates with an Azure ML endpoint for model scoring/inference.
* **pgAdmin & MinIO Console:** Built-in web dashboards to manage PostgreSQL and MinIO visually.

## 📂 Project Structure

```text
backend/
├── app/
│   ├── auth/            # Authentication routers, models, schemas, utils
│   ├── rabbits/         # Rabbits business logic, routers, models, schemas
│   ├── scans/           # Paw scan pipeline, models, schemas, routers
│   ├── database.py      # Database connection and session management
│   ├── storage.py       # MinIO client and object storage helper functions
│   └── main.py          # FastAPI entry point, routers & media streaming proxy
├── docker-compose.yml   # Docker configuration for Postgres, pgAdmin & MinIO
├── .env.example         # Template for environment variables
└── README.md
```

## 🛠 Prerequisites

Make sure you have the following installed on your machine:
* [Python 3.12+](https://www.python.org/downloads/)
* [Docker & Docker Compose](https://www.docker.com/products/docker-desktop/)

## ⚙️ Getting Started

### 1. Environment Variables
Create a `.env` file in the root of the `backend` directory by copying `.env.example`:

```bash
cp .env.example .env
```

Update `.env` with your credentials:
* **Azure ML:** Set `AZURE_ML_ENDPOINT_URL` and `AZURE_ML_API_KEY`.
* **JWT Auth:** Set a secure `SECRET_KEY` and algorithm parameters.
* **Database:** Configure your `DATABASE_URL` (default maps to host port `5433`).
* **MinIO Storage:**
  * `MINIO_ENDPOINT`: Host and port for MinIO S3 API (default: `localhost:9000`).
  * `MINIO_ROOT_USER`: Admin access key / username (must match `docker-compose.yml`).
  * `MINIO_ROOT_PASSWORD`: Admin secret key / password (must match `docker-compose.yml`).
  * `MINIO_BUCKET_NAME`: Default bucket name (default: `rabbit-media`).
  * `MINIO_USE_SSL`: Set to `False` for local HTTP development.

> [!NOTE]
> `app/storage.py` requires `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` to be defined in `.env` to prevent hardcoding secrets in source control.

### 2. Start Services with Docker Compose
PostgreSQL, pgAdmin, and MinIO run as containerized services. Start them in the background:

```bash
docker-compose up -d
```

Service endpoints:
* **PostgreSQL:** Host port `5433` (mapped to container port `5432`).
* **pgAdmin Web UI:** `http://localhost:5050`
  * Email: `admin@admin.com`
  * Password: `root`
* **MinIO S3 API:** `http://localhost:9000` (used by the backend MinIO client)
* **MinIO Web Console:** `http://localhost:9001`
  * Login with `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` configured in your `.env`.

### 3. Install Python Dependencies
Create a virtual environment and install the required dependencies:

```bash
python -m venv venv
# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Activate on Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Run the Application
Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

---

## 🪣 MinIO Object Storage Setup & Architecture

### Bucket Architecture (Single Bucket with Prefixes)
All media files are stored within a single configured bucket (`MINIO_BUCKET_NAME`, default: `rabbit-media`) using organized prefixes:
* **Avatars (`avatars/`):** `avatars/{rabbit_id}.{ext}` — stores rabbit profile pictures.
* **Scans (`scans/`):** `scans/{rabbit_id}/{photo_id}.{ext}` — stores photos captured during paw checkups.

### Automatic Bucket Provisioning
When the FastAPI app starts, a startup event executes `ensure_bucket_exists()` from `app/storage.py`. It checks whether `MINIO_BUCKET_NAME` exists in the MinIO server and automatically creates it if it does not.

### Media Streaming Proxy (`GET /media/{file_path}`)
Instead of exposing MinIO directly to mobile devices or emulators (which often face networking and host resolution issues with `localhost:9000`), FastAPI exposes a streaming proxy endpoint:
```http
GET /media/{file_path:path}
```
* **Frontend usage:** URLs stored in database records (e.g. `Photo.image_url` or `Rabbit.image_url`) are relative paths like `/media/avatars/...` or `/media/scans/...`. The mobile client prepends the backend base URL (e.g. `http://<HOST_IP>:8000/media/...`).
* **Streaming:** FastAPI fetches the object stream from MinIO and returns a `StreamingResponse` with appropriate MIME content-type headers.

---

## 📚 API Documentation

FastAPI automatically generates interactive API documentation. Once the server is running, you can access:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🛑 Stopping Services
To stop all Docker containers (PostgreSQL, pgAdmin, MinIO) without losing data, run:
```bash
docker-compose down
```
*(Note: PostgreSQL data is persisted in volume `postgres_data`, and MinIO files are persisted in volume `minio_data`)*
