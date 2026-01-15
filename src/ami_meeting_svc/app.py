from fastapi import FastAPI

# Initialize FastAPI application
app = FastAPI(debug=True)

# add routers
from ami_meeting_svc.routers.auth import auth_router
from ami_meeting_svc.routers.meetings import meetings_router

app.include_router(auth_router)
app.include_router(meetings_router, prefix="/meetings")
