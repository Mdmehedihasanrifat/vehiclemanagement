from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import create_indexes
from routes.routes import router


app = FastAPI(title="Vehicle Allocation System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api", tags=["Vehicle Allocation"])
@app.on_event("startup")
async def startup_event():
    await create_indexes()


@app.get("/")
async def root():
    return {"message": "Vehicle Allocation System API"}