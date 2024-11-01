from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import create_indexes


app = FastAPI(title="Vehicle Allocation System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await create_indexes()


@app.get("/")
async def root():
    return {"message": "Vehicle Allocation System API"}