# ami_meeting_svc API Documentation

Base URL: /

Authentication
--------------
The service uses a JWT access token carried in an HttpOnly cookie named `access_token`.
- Cookie attributes (set by server): HttpOnly, SameSite=Lax, Secure depends on COOKIE_SECURE.
- For non-cookie clients the login endpoint also returns the JWT in the response JSON under `access_token`.

Endpoints
---------

POST /auth/login
-----------------
Description: Authenticate a user and set the `access_token` cookie.

Request JSON:
{
  "username": "alice",
  "password": "secret"
}

Success Response (200):
{
  "access_token": "<jwt-token>",
  "token_type": "bearer"
}

Behavior:
- Sets cookie `access_token` (HttpOnly, SameSite=Lax, Secure depends on configuration).
- Returns access_token in JSON for use by non-cookie clients.

Errors:
- 401 Unauthorized: Invalid credentials.
- 500 Internal Server Error: Database or server error.


POST /auth/logout
------------------
Description: Clears the `access_token` cookie to log the user out.

Request: empty body

Success Response (200):
{
  "message": "logged out"
}

Behavior:
- Server issues cookie deletion (delete_cookie on `access_token`, path `/`).

Errors:
- 500 Internal Server Error: Unexpected server error.


GET /auth/me
-------------
Description: Return information about the currently authenticated user.

Authentication: Requires the `access_token` cookie to be present and valid.

Success Response (200):
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}

Errors:
- 401 Unauthorized: Missing/invalid/expired token or user not found.

Notes
-----
- Cookie security (Secure flag) is controlled by the `COOKIE_SECURE` configuration value.
- Token expiration is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- The OpenAPI docs are available at `/docs` and the raw schema at `/openapi.json` when the app is running.

Meeting Management
------------------
The Meeting Management endpoints allow authenticated users to create and manage meeting records. All endpoints below require authentication via the `access_token` HttpOnly cookie.

Validation rules
- notes: required; minimum 50 characters (notes must be at least 50 characters long).

POST /meetings/
----------------
Description: Create a meeting owned by the current authenticated user.

Authentication: requires `access_token` cookie.

Request JSON example:
{
  "title": "Team Sync",
  "date": "2026-01-15T12:34:56.000Z",
  "attendees": ["alice", "bob"],
  "notes": "This meeting covered project updates, blockers, and next steps. Detailed notes go here..."
}

Success Response (201):
Returns the created MeetingResponse object with fields:
- id: integer
- owner_id: integer (id of the creating user)
- title: string
- date: datetime (ISO 8601)
- attendees: array of strings
- notes: string
- created_at: datetime
- updated_at: datetime

Example (201):
{
  "id": 42,
  "owner_id": 1,
  "title": "Team Sync",
  "date": "2026-01-15T12:34:56.000Z",
  "attendees": ["alice", "bob"],
  "notes": "This meeting covered project updates, blockers, and next steps. Detailed notes go here...",
  "created_at": "2026-01-15T12:35:00.000Z",
  "updated_at": "2026-01-15T12:35:00.000Z"
}

Errors:
- 401 Unauthorized: Missing or invalid token.
- 422 Unprocessable Entity: Validation error (e.g., notes too short).
- 500 Internal Server Error: Database error.

Example 422 response for notes too short (FastAPI/Pydantic style):
{
  "detail": [
    {
      "loc": ["body", "notes"],
      "msg": "notes must be at least 50 characters long",
      "type": "value_error"
    }
  ]
}

GET /meetings/
---------------
Description: List meetings for the current authenticated user (scoped by owner_id).

Authentication: requires `access_token` cookie.

Success Response (200):
An array of MeetingResponse objects (see fields under POST /meetings/ success response).

Errors:
- 401 Unauthorized
- 500 Internal Server Error

GET /meetings/{meeting_id}
---------------------------
Description: Fetch a single meeting by id if owned by the current authenticated user.

Authentication: requires `access_token` cookie.

Path parameters:
- meeting_id: integer (id of the meeting)

Success Response (200):
A single MeetingResponse object.

Errors:
- 401 Unauthorized
- 404 Not Found: Meeting does not exist or is not owned by the current user.
- 500 Internal Server Error

Notes and tips
- Ensure the `notes` field meets the validation requirement (at least 50 characters) when creating or updating meetings.
- The OpenAPI docs at `/docs` include the request/response models and can be used for interactive testing when the app is running.
