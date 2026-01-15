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

POST /meetings/{meeting_id}/analyze
------------------------------------
Description: Run AI-powered analysis on the meeting notes and persist the result to the meeting record.

Authentication: requires `access_token` HttpOnly cookie. The endpoint is protected and only the meeting owner can invoke analysis for that meeting.

Path parameters:
- meeting_id: integer (id of the meeting)

Request body: empty (no JSON payload required). The analysis runs against the meeting.notes stored in the database.

Behavior:
- Validates meeting exists and is owned by the current authenticated user.
- Validates that meeting.notes is non-empty; returns 400 if notes are empty.
- Calls the OpenAI-backed analysis service and expects a JSON object in return.
- Persists the returned JSON into the meeting.analysis_result column and returns the updated MeetingResponse.

Response structure (MeetingResponse):
- id: integer
- owner_id: integer
- title: string
- date: datetime
- attendees: array of strings
- notes: string
- created_at: datetime
- updated_at: datetime
- analysis_result: object | null

analysis_result object keys (typical):
- summary: short textual summary of the meeting
- key_discussion_points: array of important discussion bullet points
  - Note: some integrations or prompts may use the synonym key_points. The service stores whatever keys the AI returns; commonly key_discussion_points is used.
- decisions: array of decisions or action items decided during the meeting

Example success response (200):
{
  "id": 42,
  "owner_id": 1,
  "title": "Team Sync",
  "date": "2026-01-15T12:34:56.000Z",
  "attendees": ["alice", "bob"],
  "notes": "This meeting covered project updates, blockers, and next steps. Detailed notes go here...",
  "created_at": "2026-01-15T12:35:00.000Z",
  "updated_at": "2026-01-15T12:40:00.000Z",
  "analysis_result": {
    "summary": "Brief summary of the meeting.",
    "key_discussion_points": ["Status updates", "Blockers and next steps"],
    "decisions": ["Adopt new release schedule"]
  }
}

Errors:
- 401 Unauthorized: Missing or invalid token.
- 404 Not Found: Meeting not found or not owned by the current user.
- 400 Bad Request: Meeting notes are empty and cannot be analyzed.
- 500 Internal Server Error: AI service error or database error while persisting analysis.

POST /meetings/{meeting_id}/extract-actions
-------------------------------------------
Description: Extract action items from a meeting's notes using the AI service and persist them as ActionItem records.

Authentication: requires `access_token` HttpOnly cookie. Only the meeting owner may invoke this endpoint.

Path parameters:
- meeting_id: integer (id of the meeting)

Request body: empty (no JSON payload required). The endpoint reads meeting.notes and optionally meeting.analysis_result.

Behavior / Workflow:
- Validates meeting exists and is owned by the current authenticated user (404 if not).
- Validates meeting.notes is non-empty (400 if empty).
- Builds an AI prompt containing the current date, meeting.notes, and existing analysis_result when available.
- Calls the OpenAI service in JSON mode and expects an object with key "action_items" mapping to a list of action item objects.
- For each action item returned by AI, the service expects fields:
  - description (string, required)
  - assignee (string or null)
  - priority (string; one of High, Medium, Low)
  - deadline (ISO8601 string, unix timestamp number, or null)
- Deadline handling: if the AI returns null, an empty string, or an unparseable value, the server defaults the deadline to 7 days from now.
- The service constructs ActionItem rows and persists them in the database, returning the created items.

Success Response (200):
An array of ActionItemResponse objects. Each object contains the following fields:
- id: integer
- meeting_id: integer
- description: string
- assignee: string | null
- priority: string (High/Medium/Low)
- deadline: datetime | null
- status: string
- is_overdue: boolean
- created_at: datetime
- updated_at: datetime

Example success response (200):
[
  {
    "id": 101,
    "meeting_id": 42,
    "description": "Follow up with infra team about deployment windows",
    "assignee": "alice",
    "priority": "High",
    "deadline": "2026-01-22T12:00:00+00:00",
    "status": "To Do",
    "is_overdue": false,
    "created_at": "2026-01-15T13:00:00.000Z",
    "updated_at": "2026-01-15T13:00:00.000Z"
  }
]

Errors:
- 401 Unauthorized: Missing or invalid token.
- 404 Not Found: Meeting not found or not owned by the current user.
- 400 Bad Request: Meeting notes are empty.
- 500 Internal Server Error: AI service error, invalid AI response format, or database error.

Notes
-----
- The AI is expected to return strictly-formatted JSON (a single JSON object). The endpoint validates the structure and fields; invalid structures produce 500 errors.
- The OpenAI model used and API key are controlled by environment variables (see README and config.py).
- The OpenAPI docs at `/docs` include the request/response models and can be used for interactive testing when the app is running.

Action Items Management
-----------------------
This section documents Action Item related APIs for creating and updating action items that stem from meetings.
All endpoints require authentication via the `access_token` HttpOnly cookie.

PATCH /action-items/{id}
-------------------------
Description: Partially update an existing ActionItem resource. Only provided fields will be updated.

Authentication: requires `access_token` cookie (JWT).

Path parameters:
- id (action_item_id): integer (id of the action item to update)

Request Body: ActionItemUpdate (all fields optional)
- description: string | optional
- assignee: string | null | optional
- priority: string | optional (allowed values: High, Medium, Low). Values are normalized to Title Case.
- deadline: datetime (ISO 8601) | null | optional
- status: string | optional (allowed values: To Do, In Progress, Done)

Validation:
- priority, if provided, must be one of High, Medium, Low (case-insensitive normalization applied).
- status, if provided, must be exactly one of: To Do, In Progress, Done.

Behavior:
- Only fields present in the request body are applied to the stored ActionItem.
- The server recalculates the `is_overdue` boolean after applying updates using the following logic:
  is_overdue = (deadline has passed) AND (status != "Done")
  If `deadline` is null, `is_overdue` will be set to false.

Response model: ActionItemResponse
Fields returned:
- id: integer
- meeting_id: integer
- description: string
- assignee: string | null
- priority: string
- deadline: datetime | null
- status: string
- is_overdue: boolean
- created_at: datetime
- updated_at: datetime

Example Request (PATCH):
PATCH /action-items/123
Content-Type: application/json
{
  "assignee": "carol",
  "deadline": "2026-01-22T12:00:00Z",
  "status": "In Progress"
}

Example Success Response (200):
{
  "id": 123,
  "meeting_id": 42,
  "description": "Follow up with infra team about deployment windows",
  "assignee": "carol",
  "priority": "High",
  "deadline": "2026-01-22T12:00:00+00:00",
  "status": "In Progress",
  "is_overdue": false,
  "created_at": "2026-01-15T13:00:00.000Z",
  "updated_at": "2026-01-16T09:00:00.000Z"
}

Errors:
- 401 Unauthorized: Missing or invalid token.
- 404 Not Found: Action item with the provided id does not exist.
- 422 Unprocessable Entity: Invalid `status` or `priority` value or malformed datetime.
- 500 Internal Server Error: Database error while saving updates.

Notes and examples:
- Allowed status values: To Do, In Progress, Done
- The `is_overdue` calculation is deterministic and performed by the server according to the rule above.

Notes and tips
- Ensure the `notes` field meets the validation requirement (at least 50 characters) when creating or updating meetings if you want AI analysis or extraction to proceed.
- The OpenAI model used and API key are controlled by environment variables (see README and config.py).
- The OpenAPI docs at `/docs` include the request/response models and can be used for interactive testing when the app is running.
