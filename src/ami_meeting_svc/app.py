from fastapi import FastAPI

app = FastAPI(debug=True, root_path=ami_meeting_svc)

# add routers