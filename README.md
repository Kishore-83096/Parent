# PARROT Parent Service

The PARROT Parent Service is a Flask-based backend for parent account management in the PARROT system. It handles registration, login, JWT-based authentication, profile management, profile-picture upload to Cloudinary, password changes, verified account deletion, service health checks, and database inspection endpoints used for testing and diagnostics.

## What This Service Does

- Creates parent accounts
- Logs users in with JWT access and refresh tokens
- Stores parent profile data
- Uploads, replaces, compresses, and removes profile pictures with Cloudinary
- Lets authenticated users change passwords securely
- Lets authenticated users delete their account only after identity verification
- Exposes health and database-check endpoints for debugging and monitoring

## Tech Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Alembic
- Marshmallow
- Flask-JWT-Extended
- PostgreSQL or SQLite
- Cloudinary
- Gunicorn
- Waitress
- Docker

## Folder Structure

```text
Parent/
|-- app/
|   |-- main/
|   |   |-- api/
|   |   |   |-- errors.py          # Global API error handling
|   |   |   |-- model.py           # User and Profile models
|   |   |   |-- routes.py          # Main API routes
|   |   |   |-- schema.py          # Marshmallow request/response schemas
|   |   |   `-- services.py        # Main API business logic
|   |   |-- health/
|   |   |   |-- routes.py          # Health and schema routes
|   |   |   |-- services.py        # Health and DB logic
|   |   |   `-- templates/
|   |   |       `-- db_schema.html # HTML DB schema/table viewer
|   |   `-- __init__.py
|   |-- utils/
|   |   |-- decorators.py
|   |   `-- __init__.py
|   |-- __init__.py                # App factory
|   |-- config.py                  # Config and environment handling
|   |-- models.py                  # Compatibility re-export
|   |-- schemas.py                 # Compatibility re-export
|   `-- __pycache__/
|-- migrations/                    # Alembic migrations
|-- Dockerfile
|-- docker-compose.yml
|-- Procfile
|-- requirements.txt
|-- run.py                         # Local development entrypoint
`-- wsgi.py                        # Production WSGI entrypoint
```

## Environment Variables

Create a `.env` file for local or Docker-based runs:

```env
APP_ENV=development
FLASK_ENV=development
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
DATABASE_URL=sqlite:///parent.db
CLOUDINARY_URL=your_cloudinary_url
CLOUDINARY_PROFILE_FOLDER=MAIN/Display_pics
PORT=5000
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=120
```

Important notes:

- `DATABASE_URL` can point to SQLite for local development or PostgreSQL in production.
- `CLOUDINARY_URL` is required for profile picture uploads.
- `CLOUDINARY_PROFILE_FOLDER` controls where images are stored in Cloudinary.

## Running Locally

Install dependencies:

```powershell
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run database migrations:

```powershell
flask --app run.py db upgrade
```

Run the development server:

```powershell
python run.py
```

Base URL:

```text
http://127.0.0.1:5000
```

## Running In Production Style

### `wsgi.py`

`wsgi.py` exposes the Flask app as a WSGI application:

```python
app = create_app(config_name)
```

Production servers do not call `python run.py`. They import `wsgi:app`.

### Why Gunicorn Is Used

Gunicorn is a production WSGI server commonly used on Linux-based environments such as Render, containers, and cloud VMs.

Use Gunicorn when:

- deploying on Linux
- running inside Docker
- serving production traffic

Command:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app
```

### Why Waitress Is Used

Waitress is a production-grade WSGI server that works well on Windows. Gunicorn does not support Windows because it depends on Unix-only behavior.

Use Waitress when:

- you want a production-style server on Windows
- you want to test `wsgi:app` locally without Flask's dev server

Command:

```powershell
waitress-serve --listen=0.0.0.0:5000 wsgi:app
```

### When To Use `run.py`, `wsgi.py`, Gunicorn, And Waitress

- `python run.py`: local development and quick testing
- `wsgi.py`: the WSGI app entrypoint imported by production servers
- `gunicorn wsgi:app`: Linux production server
- `waitress-serve ... wsgi:app`: Windows production-style server

## Why Docker Is Used

Docker packages the service, Python runtime, dependencies, and production command into a single reproducible environment. This reduces machine-specific issues and makes local testing closer to production.

Benefits:

- consistent runtime across machines
- easier deployment
- isolated dependency management
- simpler production startup
- predictable container networking and environment configuration

## Docker Commands

Build the image:

```powershell
docker build -t parrot-parent:local .
```

Run the container directly:

```powershell
docker run --env-file .env -p 5000:5000 --name parrot-parent parrot-parent:local
```

Run with Docker Compose:

```powershell
docker compose up --build
```

Run in detached mode:

```powershell
docker compose up -d --build
```

Stop Compose services:

```powershell
docker compose down
```

Restart Compose services:

```powershell
docker compose restart
```

See running containers:

```powershell
docker ps
```

See container logs:

```powershell
docker logs parrot-parent
```

Follow logs continuously:

```powershell
docker logs -f parrot-parent
```

Open a shell inside the running container:

```powershell
docker exec -it parrot-parent sh
```

Run migrations inside the container:

```powershell
docker exec -it parrot-parent flask --app run.py db upgrade
```

## Dockerfile And Compose Behavior

### Dockerfile

The Dockerfile:

- starts from `python:3.12-slim`
- installs dependencies from `requirements.txt`
- copies `app/`, `migrations/`, `run.py`, `wsgi.py`, and `Procfile`
- runs the app with Gunicorn
- exposes port `5000`

Container startup command:

```bash
gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout ${GUNICORN_TIMEOUT:-120} wsgi:app
```

### docker-compose.yml

The compose file:

- builds from the local project directory
- loads environment variables from `.env`
- maps container port `5000` to host port `5000`
- restarts automatically unless stopped

## API Overview

There are two groups of routes:

- main parent API routes under `/parent/...`
- health and database routes at the root level

### API Summary Table

| Route | Method | Auth Required | Request Body | Success Response | Error Cases |
|---|---|---|---|---|---|
| `/` | `GET` | No | None | `{"message": "Hai to the Parent service of Parrot."}` | Usually none unless server error |
| `/health` | `GET` | No | None | `{"status": "ok"}` | Usually none unless server error |
| `/db/health` | `GET` | No | None | `{"database": "connected"}` | `{"database": "disconnected", "error": "..."}` |
| `/db/schema` | `GET` | No | None | HTML schema viewer page | Server or database errors |
| `/parent/auth/register` | `POST` | No | `{"username","password","confirm_password","first_name","last_name"}` | `{"message":"User registered successfully.","user":{...}}` | password mismatch, short password, invalid username, duplicate username, duplicate email |
| `/parent/auth/login` | `POST` | No | `{"username","password"}` | `{"access_token":"...","refresh_token":"...","user":{...}}` | invalid username or password, validation errors |
| `/parent/auth/refresh` | `POST` | Refresh token | None | `{"access_token":"..."}` | missing token, invalid token, expired token |
| `/parent/auth/change-password` | `POST` | Access token | `{"username","email","current_password","new_password"}` | `{"message":"Password changed successfully."}` | wrong username, email, or current password; same new password; short new password; missing token |
| `/parent/profile/` | `GET` | Access token | None | profile JSON | profile not found, missing token, invalid token |
| `/parent/profile/` | `PUT` | Access token | JSON or form-data with profile fields and optional `profile_picture` | updated profile JSON | invalid `card_type`, invalid image type, image cannot compress to `50 KB`, user not found, validation errors, missing token |
| `/parent/profile/picture` | `DELETE` | Access token | None | `{"message":"Profile picture removed successfully."}` | profile not found, profile picture not found, missing token |
| `/parent/account` | `DELETE` | Access token | `{"username","email","password"}` | `{"message":"Account deleted successfully."}` | wrong username, email, or password; user not found; validation errors; missing token |

## Response Style

The service returns JSON for main APIs and error handling. The only HTML route is `GET /db/schema`.

Common response patterns:

- success with JSON body
- validation failure with `message` and `errors`
- authentication or authorization failure with `message`
- database/server failure with `message`

## Health And Diagnostics Routes

### `GET /`

Purpose:

- confirms the service is reachable

Success response:

```json
{
  "message": "Hai to the Parent service of Parrot."
}
```

### `GET /health`

Purpose:

- basic service health check

Success response:

```json
{
  "status": "ok"
}
```

### `GET /db/health`

Purpose:

- checks whether the database connection is working

Success response:

```json
{
  "database": "connected"
}
```

Failure response example:

```json
{
  "database": "disconnected",
  "error": "database error details"
}
```

### `GET /db/schema`

Purpose:

- renders an HTML page showing database tables, columns, constraints, and rows

Response type:

- HTML, not JSON

Warning:

- this route exposes schema and row data
- keep it for local/admin/test use only

## Main API Routes

### `POST /parent/auth/register`

Purpose:

- creates a new parent account

Request body:

```json
{
  "username": "parentdemo",
  "password": "Parent123",
  "confirm_password": "Parent123",
  "first_name": "Priya",
  "last_name": "Sharma"
}
```

Functionality:

- validates username format
- validates password length
- checks `confirm_password`
- converts username to lowercase
- auto-generates email as `username@epost.com`
- generates a unique account number starting with `7`
- creates a related profile record

Success response:

```json
{
  "message": "User registered successfully.",
  "user": {
    "id": 1,
    "username": "parentdemo",
    "email": "parentdemo@epost.com",
    "account_number": "7XXXXXXXXX",
    "is_premium": false,
    "created_at": "2026-05-04T00:00:00+00:00"
  }
}
```

Validation failure example:

```json
{
  "errors": {
    "confirm_password": [
      "Passwords do not match."
    ]
  }
}
```

Duplicate username or email example:

```json
{
  "message": "Username is already registered."
}
```

### `POST /parent/auth/login`

Purpose:

- authenticates a user and returns JWT tokens

Request body:

```json
{
  "username": "parentdemo",
  "password": "Parent123"
}
```

Functionality:

- validates credentials
- returns `access_token`
- returns `refresh_token`
- returns current user data

Success response:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "user": {
    "id": 1,
    "username": "parentdemo",
    "email": "parentdemo@epost.com"
  }
}
```

Failure response:

```json
{
  "message": "Invalid username or password."
}
```

### `POST /parent/auth/refresh`

Purpose:

- issues a new access token using a refresh token

Headers:

```text
Authorization: Bearer <refresh_token>
```

Success response:

```json
{
  "access_token": "<new-jwt>"
}
```

Failure examples:

```json
{
  "message": "Missing Authorization Header"
}
```

```json
{
  "message": "Token has expired."
}
```

### `POST /parent/auth/change-password`

Purpose:

- changes the logged-in user's password after identity verification

Headers:

```text
Authorization: Bearer <access_token>
```

Request body:

```json
{
  "username": "parentdemo",
  "email": "parentdemo@epost.com",
  "current_password": "Parent123",
  "new_password": "Parent456"
}
```

Functionality:

- checks that the JWT belongs to a real user
- verifies the provided `username`, `email`, and `current_password`
- rejects reuse of the current password
- saves the new password as a hash

Success response:

```json
{
  "message": "Password changed successfully."
}
```

Failure examples:

```json
{
  "message": "Username, email, or current password is incorrect."
}
```

```json
{
  "message": "New password must be different from the current password."
}
```

```json
{
  "errors": {
    "new_password": [
      "Shorter than minimum length 8."
    ]
  }
}
```

### `GET /parent/profile/`

Purpose:

- returns the authenticated user's profile

Headers:

```text
Authorization: Bearer <access_token>
```

Functionality:

- reads the user id from JWT
- fetches the linked `profiles` record

Success response:

```json
{
  "id": 1,
  "user_id": 1,
  "first_name": "Priya",
  "last_name": "Sharma",
  "phone": "+91-9876543210",
  "profile_picture": "https://res.cloudinary.com/...",
  "card_number": "4111111111111111",
  "card_name": "Priya Sharma",
  "card_type": "credit",
  "dr_no": "12A",
  "floor": "3",
  "street": "Lake View Road",
  "area": "Indiranagar",
  "city": "Bengaluru",
  "state": "Karnataka",
  "country": "India",
  "updated_at": "2026-05-04T00:00:00+00:00"
}
```

Failure examples:

```json
{
  "message": "Profile not found."
}
```

```json
{
  "message": "Missing Authorization Header"
}
```

### `PUT /parent/profile/`

Purpose:

- creates or updates the authenticated user's profile

Headers:

```text
Authorization: Bearer <access_token>
```

JSON example:

```json
{
  "phone": "+91-9876543210",
  "card_number": "4111111111111111",
  "card_name": "Priya Sharma",
  "card_type": "credit",
  "dr_no": "12A",
  "floor": "3",
  "street": "Lake View Road",
  "area": "Indiranagar",
  "city": "Bengaluru",
  "state": "Karnataka",
  "country": "India"
}
```

Form-data example:

```text
first_name = Priya
last_name = Sharma
phone = +91-9876543210
profile_picture = <image file>
```

Functionality:

- supports JSON and multipart form-data
- creates a profile if one does not already exist
- validates `card_type` as `credit` or `debit`
- uploads profile pictures to Cloudinary
- if the uploaded image is over `50 KB`, attempts compression down to `50 KB`
- if an old profile picture exists, deletes it from Cloudinary before replacing it

Success response:

```json
{
  "id": 1,
  "user_id": 1,
  "first_name": "Priya",
  "last_name": "Sharma",
  "phone": "+91-9876543210",
  "profile_picture": "https://res.cloudinary.com/...",
  "card_type": "credit",
  "city": "Bengaluru",
  "state": "Karnataka",
  "country": "India"
}
```

Failure examples:

```json
{
  "message": "Profile picture must be a jpg, jpeg, png, or webp file."
}
```

```json
{
  "message": "Unable to compress profile picture to 50 KB."
}
```

```json
{
  "errors": {
    "card_type": [
      "Must be one of: credit, debit."
    ]
  }
}
```

### `DELETE /parent/profile/picture`

Purpose:

- deletes only the profile picture, not the profile or account

Headers:

```text
Authorization: Bearer <access_token>
```

Functionality:

- checks that the authenticated user has a profile
- checks that a profile picture exists
- removes the image from Cloudinary
- sets `profile_picture` to `null`

Success response:

```json
{
  "message": "Profile picture removed successfully."
}
```

Failure examples:

```json
{
  "message": "Profile not found."
}
```

```json
{
  "message": "Profile picture not found."
}
```

### `DELETE /parent/account`

Purpose:

- deletes the authenticated user's entire account after confirmation

Headers:

```text
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request body:

```json
{
  "username": "parentdemo",
  "email": "parentdemo@epost.com",
  "password": "Parent456"
}
```

Functionality:

- verifies the logged-in user
- checks `username`, `email`, and `password`
- deletes the Cloudinary profile picture if present
- deletes the user account
- removes the related profile through cascade delete

Success response:

```json
{
  "message": "Account deleted successfully."
}
```

Failure examples:

```json
{
  "message": "Username, email, or password is incorrect."
}
```

```json
{
  "message": "User not found."
}
```

## Global Error Handling

Main API routes use centralized error handling in `app/main/api/errors.py`.

Handled cases include:

- Marshmallow validation errors
- JWT authorization errors
- invalid tokens
- expired tokens
- HTTP exceptions
- SQLAlchemy database exceptions
- unexpected server exceptions

Typical error response shapes:

```json
{
  "message": "Validation failed.",
  "errors": {
    "field_name": [
      "error message"
    ]
  }
}
```

```json
{
  "message": "Missing Authorization Header"
}
```

```json
{
  "message": "Token has expired."
}
```

```json
{
  "message": "A database error occurred."
}
```

```json
{
  "message": "An unexpected error occurred."
}
```

## Database Migrations

Apply existing migrations:

```powershell
flask --app run.py db upgrade
```

Create a new migration:

```powershell
flask --app run.py db migrate -m "describe your change"
```

Apply the new migration:

```powershell
flask --app run.py db upgrade
```

## Production Notes

- Use Gunicorn in Linux and Docker deployments.
- Use Waitress when you need a production-style Windows server.
- Keep `/db/schema` protected or disabled in public production environments.
- Never commit `.env`.
- Set all secrets through environment variables in production.
