from pydantic import BaseModel
from datetime import date

class AllocationCreate(BaseModel):
    employee_id: str
    vehicle_id: str
    allocation_date: date

class AllocationUpdate(BaseModel):
    allocation_date: date

class AllocationResponse(BaseModel):
    allocation_id: str
    employee_id: str
    vehicle_id: str
    allocation_date: date
    created_at: str
    updated_at: str
