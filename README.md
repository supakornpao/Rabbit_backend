# Rabbit Backend (FastAPI)

This is the backend service for the Rabbit application, built with **FastAPI** and **PostgreSQL**. It includes JWT-based authentication, a module for managing rabbits, and integration with an Azure Machine Learning endpoint for inference.

## 🚀 Features

* **FastAPI Framework:** High-performance, modern Python web framework.
* **PostgreSQL Database:** Relational database running via Docker.
* **JWT Authentication:** Secure user signup, login, and protected routes (`/auth`).
* **Rabbits Module:** Core business logic and API endpoints for managing rabbits (`/rabbits`).
* **Azure ML Integration:** Communicates with an Azure ML endpoint for model scoring/inference.
* **pgAdmin:** Built-in web UI to visually manage your PostgreSQL database.

## 📂 Project Structure

```text
backend/
├── app/
│   ├── auth/            # Authentication routers, models, schemas, utils
│   ├── rabbits/         # Rabbits business logic, routers, models, schemas
│   ├── database.py      # Database connection and session management
│   └── main.py          # FastAPI application entry point
├── docker-compose.yml   # Docker configuration for Postgres & pgAdmin
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
Update the `.env` file with your actual credentials:
* **Azure ML:** Set `AZURE_ML_ENDPOINT_URL` and `AZURE_ML_API_KEY`.
* **JWT Auth:** Set a secure `SECRET_KEY`.
* **Database:** Configure your `DATABASE_URL` (the default assumes the local Docker database).

### 2. Start the Database (Docker)
The PostgreSQL database and pgAdmin run in Docker containers. Start them in the background using:

```bash
docker-compose up -d
```

* **PostgreSQL** will be available on host port `5433` (mapped to avoid conflicts).
* **pgAdmin** will be available at `http://localhost:5050` 
  * Email: `admin@admin.com`
  * Password: `root`

### 3. Install Python Dependencies
Create a virtual environment and install the required dependencies (assuming you have a `requirements.txt`):

```bash
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
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

## 📚 API Documentation

FastAPI automatically generates interactive API documentation. Once the server is running, you can access:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🛑 Stopping the Database
To stop the database and pgAdmin containers without losing data, run:
```bash
docker-compose down
```
*(Note: Data is persisted in a Docker volume named `postgres_data`)*
