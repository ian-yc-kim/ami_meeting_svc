# ami_meeting_svc

ami_meeting_svc is a FastAPI service for meeting management and authentication.

Tech stack
- Python 3.11+
- FastAPI
- SQLAlchemy (Alembic for migrations)
- JWT cookie-based authentication

Prerequisites
- Python 3.11+
- Poetry (for dependency management)

Quickstart (development)
1. Install dependencies:

```bash
make build
```

2. Apply migrations / setup database:

```bash
make setup
```

3. Run the service locally:

```bash
make run
```

4. Run tests:

```bash
make unittest
```

Environment
- Configuration is loaded from environment variables. Common vars:
  - DATABASE_URL (sqlite example: sqlite:///local.db)
  - SECRET_KEY
  - ALGORITHM
  - ACCESS_TOKEN_EXPIRE_MINUTES
  - COOKIE_SECURE (true/false)
  - OPENAI_API_KEY (required for OpenAI integration; credential)
  - OPENAI_MODEL_NAME (optional; default gpt-3.5-turbo)

API docs
- Interactive API docs: /docs
- OpenAPI JSON: /openapi.json
- Additional, human-written auth docs: API.md

Project layout
- src/ami_meeting_svc: application package
- tests: pytest-based unit tests

See API.md for detailed Authentication API documentation.
