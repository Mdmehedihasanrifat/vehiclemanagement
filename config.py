
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")  
print(MONGODB_URL)
client = AsyncIOMotorClient(MONGODB_URL, server_api=ServerApi('1'))
database = client.vehicle_allocation

# Create indexes for optimization
async def create_indexes():
    await database.vehicles.create_index("vehicle_id", unique=True)
    await database.drivers.create_index("driver_id", unique=True)
    await database.employees.create_index("employee_id", unique=True)
    # Compound index for allocation checks
    await database.allocations.create_index([
        ("vehicle_id", 1),
        ("allocation_date", 1)
    ], unique=True)
    # Index for history reports
    await database.allocations.create_index([
        ("allocation_date", -1),
        ("employee_id", 1)
    ])



