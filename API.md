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
