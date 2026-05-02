# PARROT Parent Service

Flask API service for the Parent module of PARROT. It provides parent account registration, login with JWT, profile management, profile picture uploads to Cloudinary, database health checks, and database schema inspection for testing.

## Tech Stack

- Python 3.12
- Flask: web framework for building the API.
- Flask-SQLAlchemy: database ORM for models and queries.
- Flask-JWT-Extended: JWT authentication for protected routes.
- Flask-Migrate / Alembic: database migrations.
- PostgreSQL: production database.
- Cloudinary: profile picture storage.
- Marshmallow: request validation and response serialization.
- Gunicorn: production WSGI server for Linux/Render.
- Waitress: production-style WSGI server for Windows local testing.
- Docker: containerized deployment.

## Folder Structure

```text
Parent/
├── app/
│   ├── resources/
│   │   ├── auth.py          # Register, login, refresh token
│   │   ├── health.py        # Health, database health, schema viewer
│   │   └── profile.py       # Profile CRUD and profile picture upload
│   ├── templates/
│   │   └── db_schema.html   # Browser database schema/table viewer
│   ├── utils/
│   │   └── decorators.py    # Custom decorators
│   ├── __init__.py          # Flask app factory and blueprint registration
│   ├── config.py            # App/database/cloud config
│   ├── models.py            # User and Profile database models
│   └── schemas.py           # Marshmallow validation schemas
├── migrations/              # Alembic migration files
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Local Docker run
├── Procfile                 # Render-style process command
├── requirements.txt         # Python packages
├── run.py                   # Local direct runner
├── wsgi.py                  # Production WSGI entrypoint
└── .env                     # Local secrets, not committed
```

## Environment Variables

Create `.env` locally:

```env
APP_ENV=production
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_URL=your_postgres_database_url
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
CLOUDINARY_URL=your_cloudinary_url
CLOUDINARY_PROFILE_FOLDER=MAIN/Display_pics
```

Do not commit `.env`.

## Run Locally

Development/direct run:

```powershell
python run.py
```

Production-style run on Windows:

```powershell
waitress-serve --listen=0.0.0.0:5000 wsgi:app
```

Production-style run on Linux/Render:

```bash
gunicorn wsgi:app
```

Docker:

```powershell
docker compose up --build
```

Base URL locally:

```text
http://127.0.0.1:5000
```

## WSGI, Gunicorn, Waitress, And Docker

### Why `wsgi.py` Exists

`wsgi.py` exposes the Flask app as a WSGI application:

```python
app = create_app(config_name)
```

Deployment servers like Gunicorn and Waitress need this object. They import `wsgi:app` and serve it. This is better for production than using Flask's built-in development server.

Use `run.py` for direct local runs:

```powershell
python run.py
```

Use `wsgi.py` for production servers:

```text
wsgi:app
```

### Why Gunicorn

Gunicorn is a production WSGI server commonly used on Linux hosting platforms like Render.

Use it on Render/Linux:

```bash
gunicorn wsgi:app
```

In Docker, the service starts with:

```bash
gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout ${GUNICORN_TIMEOUT:-120} wsgi:app
```

Gunicorn does not work on Windows because it depends on Unix-only modules like `fcntl`.

### Why Waitress

Waitress is a production-style WSGI server that works on Windows.

Use it for local Windows testing:

```powershell
waitress-serve --listen=0.0.0.0:5000 wsgi:app
```

This lets you test the same `wsgi:app` production entrypoint without using Flask's development server.

### Why Docker

Docker packages the service, dependencies, and production command into one container image. This makes local testing and deployment more consistent.

The Docker image copies only needed files:

```text
app/
migrations/
run.py
wsgi.py
Procfile
requirements.txt
```

It excludes local-only files:

```text
venv/
.env
__pycache__/
instance/
app/static/uploads/
.git/
```

Build the image:

```powershell
docker build -t parrot-parent:local .
```

Run the image:

```powershell
docker run --env-file .env -p 5000:5000 parrot-parent:local
```

Run with Docker Compose:

```powershell
docker compose up --build
```

Stop Docker Compose:

```powershell
docker compose down
```

View running containers:

```powershell
docker ps
```

View logs:

```powershell
docker logs parrot-parent
```

If Docker is installed but PowerShell says `docker` is not recognized, add Docker CLI to the current terminal PATH:

```powershell
$env:Path = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:Path
```

## Test APIs

### Root

```text
GET /
```

Response:

```json
{
  "message": "Hai to the Parent service of Parrot."
}
```

### Service Health

```text
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Database Health

```text
GET /db/health
```

Response:

```json
{
  "database": "connected"
}
```

### Database Schema Viewer

```text
GET /db/schema
```

Opens a browser page showing database tables, columns, constraints, and row data.

Important: this endpoint exposes database structure and table rows. Keep it for local/admin testing only, or protect/remove it before public production use.

## Main APIs

### Register Parent

```text
POST /parent/auth/register
```

Postman:

- Method: `POST`
- URL: `http://127.0.0.1:5000/parent/auth/register`
- Headers: `Content-Type: application/json`
- Body: raw JSON

```json
{
  "username": "testparent1",
  "password": "password123",
  "first_name": "Test",
  "last_name": "Parent"
}
```

Notes:

- Email is generated automatically as `username@epost.com`.
- A unique 10-digit account number starting with `7` is generated automatically.

### Login

```text
POST /parent/auth/login
```

Postman:

- Method: `POST`
- URL: `http://127.0.0.1:5000/parent/auth/login`
- Headers: `Content-Type: application/json`
- Body: raw JSON

```json
{
  "username": "testparent1",
  "password": "password123"
}
```

Copy `access_token` from the response for protected APIs.

### Refresh Token

```text
POST /parent/auth/refresh
```

Postman:

- Method: `POST`
- URL: `http://127.0.0.1:5000/parent/auth/refresh`
- Headers:

```text
Authorization: Bearer YOUR_REFRESH_TOKEN
```

### Get Profile

```text
GET /parent/profile/
```

Postman headers:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Update Profile With JSON

```text
PUT /parent/profile/
```

Postman:

- Method: `PUT`
- URL: `http://127.0.0.1:5000/parent/profile/`
- Headers:

```text
Content-Type: application/json
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Body:

```json
{
  "first_name": "Test",
  "last_name": "Parent",
  "phone": "9876543210",
  "profile_picture": "https://example.com/profile.jpg",
  "card_number": "4111111111111111",
  "card_name": "Test Parent",
  "card_type": "credit",
  "dr_no": "12A",
  "floor": "2",
  "street": "Main Street",
  "area": "Central Area",
  "city": "Chennai",
  "state": "Tamil Nadu",
  "country": "India"
}
```

`card_type` must be:

```text
credit
debit
```

### Update Profile With Form-Data And Image

```text
PUT /parent/profile/
```

Postman:

- Method: `PUT`
- URL: `http://127.0.0.1:5000/parent/profile/`
- Headers:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

- Body: `form-data`

```text
first_name          Test
last_name           Parent
phone               9876543210
card_number         4111111111111111
card_name           Test Parent
card_type           credit
dr_no               12A
floor               2
street              Main Street
area                Central Area
city                Chennai
state               Tamil Nadu
country             India
profile_picture     choose file
```

Set `profile_picture` field type to `File` in Postman.

Allowed file types:

```text
jpg, jpeg, png, webp
```

Uploaded profile pictures are stored in Cloudinary folder:

```text
MAIN/Display_pics
```

The profile table stores the Cloudinary `secure_url`.

### Delete Profile

```text
DELETE /parent/profile/
```

Postman headers:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Database Tables

Current main tables:

- `users`
- `profiles`
- `alembic_version`

Run migrations:

```powershell
flask --app run.py db upgrade
```

Create a new migration after model changes:

```powershell
flask --app run.py db migrate -m "Migration message"
flask --app run.py db upgrade
```

## Deployment Notes

For Render Docker deployment:

- Use Docker service.
- Set environment variables in Render dashboard.
- Do not upload `.env`.
- Dockerfile starts the app with Gunicorn.

Health check URL:

```text
/health
```
