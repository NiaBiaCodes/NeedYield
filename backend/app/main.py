from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.routes import ai, donations, health, locations, matching, organization_assistant, organizations, rag, reservations, resources

app = FastAPI(title="NeedYield API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+):\d+$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Demo-User", "X-Demo-Role", "X-Demo-Admin"],
)

for router in (health.router, locations.router, resources.router, ai.router, matching.router, reservations.router, donations.router, organizations.router, organization_assistant.router, rag.router):
    app.include_router(router)
