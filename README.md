# PARROT Parent Service

The PARROT Parent Service is a Flask-based backend for account, profile, contact, and privacy-policy management in the PARROT system. It handles registration, login, JWT-based authentication, profile management, profile-picture upload to Cloudinary, saved contacts, block and ghost rules, password changes, verified account deletion, Messenger JWT issuing, internal Messenger policy checks, service health checks, and local database inspection endpoints used for testing and diagnostics.

## What This Service Does

- Creates parent accounts
- Logs users in with JWT access and refresh tokens
- Issues short-lived Messenger JWTs for the Messenger service
- Stores parent profile data
- Authorizes Messenger service requests for text, attachment, voice-note, audio, video, edit, delete, story, and group flows against saved-contact, block, and ghost rules
- Stores saved-contact aliases plus `blocked` and `ghosted` privacy flags
- Resolves internal presence, receipt, story-audience, story-visibility, and group-member policies for Messenger
- Provides a local development bridge for triggering Messenger expired-story cleanup from the DB schema page
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
|   |   |   |-- cache.py           # 5-minute in-memory profile cache
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
INTERNAL_SERVICE_TOKEN=shared_internal_service_token
MESSENGER_SERVICE_URL=http://127.0.0.1:8000
MESSENGER_SERVICE_TIMEOUT_SECONDS=5
MESSAGING_JWT_SECRET=shared_messenger_jwt_secret
MESSAGING_JWT_ISSUER=parrot-parent
MESSAGING_JWT_AUDIENCE=parrot-messenger
MESSAGING_TOKEN_TTL_SECONDS=300
PORT=5000
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=120
```

Important notes:

- `DATABASE_URL` can point to SQLite for local development or PostgreSQL in production.
- `CLOUDINARY_URL` is required for profile picture uploads.
- `CLOUDINARY_PROFILE_FOLDER` controls where images are stored in Cloudinary.
- `INTERNAL_SERVICE_TOKEN` must match the Messenger service token for internal APIs.
- `MESSENGER_SERVICE_URL` is used by local diagnostics to call Messenger story cleanup.
- `MESSAGING_JWT_SECRET`, issuer, and audience must match Messenger settings.

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

`run.py` is the local development entrypoint. It loads the `development` config by default, even if `.env` contains production values for `APP_ENV` or `FLASK_ENV`. To override this local runner, set `LOCAL_APP_ENV`.

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
| `/db/schema` | `GET` | Local development only | None | HTML schema viewer page | `404` outside local development; server or database errors |
| `/db/schema/stories/cleanup-expired` | `POST` | Local development only | None | redirects back to DB schema page with cleanup status | `404` outside local development; Messenger cleanup errors |
| `/parent/auth/register` | `POST` | No | `{"username","password","confirm_password","first_name","last_name"}` | `{"message":"User registered successfully.","user":{...}}` | password mismatch, short password, invalid username, duplicate username, duplicate email |
| `/parent/auth/login` | `POST` | No | `{"username","password"}` | `{"access_token":"...","refresh_token":"...","user":{...}}` | invalid username or password, validation errors |
| `/parent/auth/refresh` | `POST` | Refresh token | None | `{"access_token":"..."}` | missing token, invalid token, expired token |
| `/parent/messaging/token` | `POST` | Access token | None | `{"messaging_token":"...","token_type":"Bearer","expires_in":300}` | missing token, invalid token, missing messaging secret |
| `/parent/internal/messaging/authorize` | `POST` | Internal service token | `{"sender_user_id":5,"recipient_account_number":"7XXXXXXXXX"}` | `{"allowed":true,...}` | missing internal token, sender or recipient not found, contact not saved, self-message |
| `/parent/internal/presence/visibility` | `POST` | Internal service token | owner/viewer plus candidate user ids | hidden user id lists | missing internal token, validation errors |
| `/parent/internal/receipts/visibility` | `POST` | Internal service token | owner plus candidate user ids | hidden receipt user id lists | missing internal token, validation errors |
| `/parent/internal/stories/audience` | `POST` | Internal service token | story owner plus audience account numbers | valid/excluded story audience contacts | missing internal token, validation errors |
| `/parent/internal/stories/visibility` | `POST` | Internal service token | owner/viewer identifiers | story visibility decision | missing internal token, validation errors |
| `/parent/internal/groups/members/resolve` | `POST` | Internal service token | owner plus member account numbers | valid saved-contact member records | missing internal token, validation errors |
| `/parent/auth/change-password` | `POST` | Access token | `{"username","email","current_password","new_password"}` | `{"message":"Password changed successfully."}` | wrong username, email, or current password; same new password; short new password; missing token |
| `/parent/profile/` | `GET` | Access token | None | profile JSON | profile not found, missing token, invalid token |
| `/parent/users/search` | `POST` | Access token | `{"account_number":"7XXXXXXXXX"}` | `{"first_name":"...","last_name":"...","username":"...","profile_picture":"..."}` | missing or invalid account number, phone number not in Parrot, missing token |
| `/parent/contacts` | `GET` | Access token | None | `{"contacts":[...]}` | missing token |
| `/parent/contacts/<account_number>` | `GET` | Access token | None | `{"contact":{...}}` | missing or invalid account number, contact not found, missing token |
| `/parent/contacts` | `POST` | Access token | `{"account_number":"7XXXXXXXXX","alias_name":"Mom"}` | saved contact JSON | missing or invalid account number, blank alias, own account, phone number not in Parrot, missing token |
| `/parent/contacts/alias` | `PATCH` | Access token | `{"account_number":"7XXXXXXXXX","alias_name":"Amma"}` | updated contact JSON | contact not found, blank alias, missing token |
| `/parent/contacts/block` | `POST` | Access token | `{"account_number":"7XXXXXXXXX"}` | blocked contact JSON | contact not found, phone number not in Parrot, missing token |
| `/parent/contacts/unblock` | `POST` | Access token | `{"account_number":"7XXXXXXXXX"}` | unblocked contact JSON | contact not found, phone number not in Parrot, missing token |
| `/parent/contacts/ghost` | `POST` | Access token | `{"account_number":"7XXXXXXXXX"}` | ghosted contact JSON | contact not found, phone number not in Parrot, missing token |
| `/parent/contacts/unghost` | `POST` | Access token | `{"account_number":"7XXXXXXXXX"}` | unghosted contact JSON | contact not found, phone number not in Parrot, missing token |
| `/parent/contacts` | `DELETE` | Access token | `{"account_number":"7XXXXXXXXX"}` | `{"message":"Contact deleted successfully."}` | contact not found, phone number not in Parrot, missing token |
| `/parent/profile/` | `PUT` | Access token | JSON or form-data with profile fields and optional `profile_picture` | updated profile JSON | invalid `card_type`, invalid image type, image cannot compress to `50 KB`, user not found, validation errors, missing token |
| `/parent/profile/picture` | `DELETE` | Access token | None | `{"message":"Profile picture removed successfully."}` | profile not found, profile picture not found, Cloudinary deletion failure, missing token |
| `/parent/account` | `DELETE` | Access token | `{"username","email","password"}` | `{"message":"Account deleted successfully."}` | wrong username, email, or password; user not found; Cloudinary deletion failure; validation errors; missing token |

## Response Style

The service returns JSON for main APIs and error handling. The only HTML route is `GET /db/schema`, and it is available only during local development.

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
- it is enabled only by the development config
- it returns `404` outside local loopback requests or outside development mode

### `POST /db/schema/stories/cleanup-expired`

Purpose:

- local development helper shown from the DB schema page
- calls Messenger `POST /stories/internal/cleanup-expired/`
- uses `MESSENGER_SERVICE_URL` and `INTERNAL_SERVICE_TOKEN`

Response type:

- redirects back to the DB schema HTML page with a flash message

Warning:

- available only when `/db/schema` is available
- intended for local diagnostics, not public production traffic

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

### `POST /parent/messaging/token`

Purpose:

- creates a short-lived Messenger JWT for the authenticated user
- lets Messenger derive the sender from a token instead of trusting `sender_user_id` from a client request

Headers:

```text
Authorization: Bearer <parent_access_token>
```

Success response:

```json
{
  "messaging_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 300
}
```

### `POST /parent/internal/messaging/authorize`

Purpose:

- internal-only endpoint used by Messenger before allowing a text, attachment, voice-note, audio, video, story reply, story reaction, or edited direct message
- validates sender, recipient, saved-contact relationship, block state, and ghost state

Headers:

```text
X-Internal-Service-Token: <shared_internal_service_token>
```

Request body:

```json
{
  "sender_user_id": 5,
  "recipient_account_number": "7941066772"
}
```

Allowed response:

```json
{
  "allowed": true,
  "sender_user_id": 5,
  "recipient_user_id": 4,
  "recipient_account_number": "7941066772"
}
```

Block state does not deny saved-contact sends. Allowed responses include internal `delivery_blocked`, `block_context`, and `ghost_context` fields so Messenger can keep recipient-blocked messages at `sent`, hide ghosted receipt visibility, and continue enforcing privacy rules on later edits/status updates. Deny responses include `allowed: false` with a `reason`, such as `contact_not_saved` or `self_message`. Parent applies this policy the same way for text, files, voice notes, audio, video, story replies, story reactions, and edited messages because message content and media metadata stay outside Parent.

### Internal Policy Routes

These routes are internal-only and require:

```text
X-Internal-Service-Token: <shared_internal_service_token>
```

They are called by Messenger, not directly by React.

| Route | Purpose |
|---|---|
| `POST /parent/internal/presence/visibility` | returns users whose online/offline presence should be hidden because of block or ghost rules |
| `POST /parent/internal/receipts/visibility` | returns users whose delivery/read receipts should be hidden from a message owner |
| `POST /parent/internal/stories/audience` | resolves a story owner's saved contacts into allowed/excluded audience records |
| `POST /parent/internal/stories/visibility` | checks whether a viewer can see a story and whether the view should be hidden from the owner |
| `POST /parent/internal/groups/members/resolve` | validates group member account numbers against the creator's saved contacts |

Presence policy example:

```json
{
  "owner_user_id": 5,
  "candidate_user_ids": [4, 6, 7]
}
```

```json
{
  "allowed": true,
  "hidden_user_ids": [7],
  "blocked_user_ids": [],
  "ghosted_user_ids": [7]
}
```

Receipt visibility uses the same candidate-list shape, but returns `hidden_user_ids` and `visible_user_ids` for read/delivered receipt filtering.

Group member resolution request:

```json
{
  "owner_user_id": 5,
  "member_account_numbers": ["7XXXXXXXXX"]
}
```

Parent only returns members that are saved contacts of the creator. Messenger uses that result when creating groups and adding new members.

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
- caches profile data and profile-picture URL for 5 minutes

Headers:

```text
Authorization: Bearer <access_token>
```

Functionality:

- reads the user id from JWT
- returns cached profile data when available
- fetches the linked `profiles` record
- refreshes the cache after a database read

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

### `POST /parent/users/search`

Purpose:

- searches the `users` table by exact `account_number`
- returns first name, last name, username, and profile picture when the user exists

Headers:

```text
Authorization: Bearer <access_token>
```

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "first_name": "Priya",
  "last_name": "Sharma",
  "profile_picture": "https://res.cloudinary.com/...",
  "username": "parentdemo"
}
```

Failure examples:

```json
{
  "message": "Phone number not in Parrot."
}
```

```json
{
  "errors": {
    "account_number": [
      "Account number must start with 7 and contain exactly 10 digits."
    ]
  }
}
```

### `GET /parent/contacts`

Purpose:

- returns the authenticated user's saved contacts
- caches saved contacts for 5 minutes
- returns refreshed cache data after contact add, alias update, block, unblock, ghost, unghost, or delete

Headers:

```text
Authorization: Bearer <access_token>
```

Success response:

```json
{
  "contacts": [
    {
      "alias_name": "Mom",
      "account_number": "7XXXXXXXXX",
      "blocked": false,
      "ghosted": false,
      "profile_picture": "https://res.cloudinary.com/..."
    }
  ]
}
```

### `GET /parent/contacts/<account_number>`

Purpose:

- returns only the saved contact record for one saved contact
- only works for contacts saved by the authenticated user

Headers:

```text
Authorization: Bearer <access_token>
```

Success response:

```json
{
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

Failure examples:

```json
{
  "message": "Contact not found."
}
```

### `POST /parent/contacts`

Purpose:

- saves a searched user as a contact for the authenticated user
- stores the alias name chosen by the authenticated user
- updates the alias if the same contact is already saved
- refreshes the saved contacts cache after saving

Headers:

```text
Authorization: Bearer <access_token>
```

Request body:

```json
{
  "account_number": "7XXXXXXXXX",
  "alias_name": "Mom"
}
```

Success response:

```json
{
  "message": "Contact saved successfully.",
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

Failure examples:

```json
{
  "message": "Phone number not in Parrot."
}
```

```json
{
  "message": "You cannot save your own account as a contact."
}
```

```json
{
  "errors": {
    "alias_name": [
      "Alias name cannot be blank."
    ]
  }
}
```

### `PATCH /parent/contacts/alias`

Purpose:

- updates the alias name for an already saved contact

Request body:

```json
{
  "account_number": "7XXXXXXXXX",
  "alias_name": "Amma"
}
```

Success response:

```json
{
  "message": "Contact alias updated successfully.",
  "contact": {
    "alias_name": "Amma",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

### `POST /parent/contacts/block`

Purpose:

- marks a saved contact as blocked

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "message": "Contact blocked successfully.",
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": true,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

Blocking a contact automatically removes ghosting for that same contact.

### `POST /parent/contacts/unblock`

Purpose:

- marks a saved contact as not blocked

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "message": "Contact unblocked successfully.",
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

### `POST /parent/contacts/ghost`

Purpose:

- marks a saved contact as ghosted
- removes block state for that contact if it was blocked
- tells Messenger privacy refresh logic that presence and receipt visibility should be hidden where policy applies

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "message": "Contact ghosted successfully.",
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": true,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

### `POST /parent/contacts/unghost`

Purpose:

- marks a saved contact as not ghosted
- lets Messenger refresh presence and receipt visibility for that relationship

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "message": "Contact unghosted successfully.",
  "contact": {
    "alias_name": "Mom",
    "account_number": "7XXXXXXXXX",
    "blocked": false,
    "ghosted": false,
    "profile_picture": "https://res.cloudinary.com/..."
  }
}
```

### `DELETE /parent/contacts`

Purpose:

- deletes a saved contact from the authenticated user's contact list

Request body:

```json
{
  "account_number": "7XXXXXXXXX"
}
```

Success response:

```json
{
  "message": "Contact deleted successfully."
}
```

Failure example:

```json
{
  "message": "Contact not found."
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
- refreshes the 5-minute profile cache after a successful update

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
- removes the image from Cloudinary and confirms deletion
- sets `profile_picture` to `null`
- refreshes the 5-minute profile cache after removal

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
- deletes and confirms the Cloudinary profile picture first, if present
- deletes the related profile data
- deletes the user account last
- clears the profile cache after successful account deletion

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
- `/db/schema` is disabled in production and only responds to local development requests.
- Never commit `.env`.
- Set all secrets through environment variables in production.

## Current Messenger And E2EE Integration Notes

The Parent service owns account identity, saved contacts, aliases, and contact privacy policy. It does not store encrypted message keys, linked-device keys, default-device password hashes, recovery keys, message ciphertext, group messages, or story media. Those records live in the Messenger service.

Parent is still required for encrypted messaging because it issues Messenger JWTs and answers Messenger policy checks for sends, edits, presence, receipts, story visibility, and group member resolution.

### Parent Responsibilities

- Authenticate the user with Parent access and refresh JWTs.
- Return the current user id and account number to React.
- Issue short-lived Messenger JWTs from `POST /parent/messaging/token`.
- Authorize Messenger sends through `POST /parent/internal/messaging/authorize`.
- Enforce saved-contact, block, and ghost rules used by Messenger before delivery and before later edit/status policy refreshes.
- Resolve presence and receipt visibility through internal policy endpoints so ghosted or blocked relationships do not leak online state or read/delivered state.
- Resolve story audience and story visibility through internal policy endpoints.
- Resolve group member account numbers from the creator's saved contacts before Messenger creates or expands a group.
- Treat text, file, voice-note, audio, video, story reply, story reaction, and edited-message sends as the same authorization decision. Parent never receives message ciphertext, media blobs, voice-note waveform data, playback duration, story plaintext, or attachment metadata.

### Messenger JWT Contract

`POST /parent/messaging/token` signs a token with:

```json
{
  "sub": "1",
  "user_id": 1,
  "account_number": "7XXXXXXXXX",
  "iss": "parrot-parent",
  "aud": "parrot-messenger",
  "iat": 1710000000,
  "exp": 1710000300
}
```

Messenger validates the same `MESSAGING_JWT_SECRET`, issuer, and audience. React clears stale Messenger tokens on account login and rejects any stored Messenger token whose user id does not match the current Parent user.

### Device And Recovery Boundary

- Linked devices are registered in Messenger, not Parent.
- Default-device permissions and default-password updates are enforced by Messenger with signed Ed25519 device actions plus a Messenger-owned default-device password hash.
- The recovery key is created and verified in React.
- Parent never receives the recovery key or default-device password.
- Messenger stores only encrypted recovery-backup ciphertext and metadata.
- Parent logout only clears Parent auth state. React also asks Messenger to process the current signed device logout: non-default device rows and local E2EE state are removed, while the default device row and local E2EE state are retained.

When changing Parent auth/session behavior, make sure React can still call `POST /parent/messaging/token` immediately after login, because encrypted-message setup depends on that token.
