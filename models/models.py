from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, validator
from bson import ObjectId

class PydanticObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, (str, ObjectId)):
            raise ValueError("Invalid ObjectId")
        return str(v)

class AllocationBase(BaseModel):
    employee_id: str
    vehicle_id: str
    driver_id: Optional[str] = None
    allocation_date: date
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AllocationCreate(BaseModel):
    employee_id: str
    vehicle_id: str
    allocation_date: date
    status: str = "active"

    @validator('allocation_date')
    def validate_allocation_date(cls, v):
        if v < date.today():
            raise ValueError("Cannot allocate vehicle for past dates")
        return v

class AllocationInDB(AllocationBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class AllocationResponse(BaseModel):
    employee_id: str
    vehicle_id: str
    driver_id: Optional[str] = None  # Make this optional
    allocation_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    allocation_id: str
    employee_name: str
    vehicle_name: str
    driver_name: Optional[str] = None  # Also make driver_name optional

    class Config:
        json_encoders = {
            ObjectId: str  # To serialize ObjectId as string
        }

       
class AllocationUpdate(BaseModel):
    allocation_date: Optional[date] = None
    status: Optional[str] = None

    @validator('allocation_date', pre=True, always=True)
    def validate_allocation_date(cls, v):
        if v is not None and v < date.today():
            raise ValueError("Cannot allocate vehicle for past dates")
        return v