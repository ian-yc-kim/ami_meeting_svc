from fastapi import FastAPI

# Initialize FastAPI application
app = FastAPI(debug=True)

# add routers
from ami_meeting_svc.routers.auth import auth_router
from ami_meeting_svc.routers.meetings import meetings_router
from ami_meeting_svc.routers.action_items import action_items_router
from ami_meeting_svc.routers.dashboard import dashboard_router

app.include_router(auth_router)
app.include_router(meetings_router, prefix="/meetings")
app.include_router(action_items_router, prefix="/action-items")
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"]) 
