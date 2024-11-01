from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date
from bson import ObjectId
from models.models import AllocationResponse,AllocationCreate, AllocationUpdate
from config import database
from datetime import datetime
router = APIRouter()


@router.post("/allocations", response_model=AllocationResponse)
async def create_allocation(allocation: AllocationCreate):
    try:
        # Validate employee exists
        employee = await database.employees.find_one({"employee_id": allocation.employee_id})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Validate vehicle and its availability
        vehicle = await database.vehicles.find_one({"vehicle_id": allocation.vehicle_id})
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        if vehicle["status"] != "available":
            raise HTTPException(status_code=400, detail="Vehicle not available")

        # Convert allocation_date to datetime for comparison
        allocation_date = datetime.combine(allocation.allocation_date, datetime.min.time())

        # Check if vehicle is already allocated for the date
        existing = await database.allocations.find_one({
            "vehicle_id": allocation.vehicle_id,
            "allocation_date": allocation_date,
            "status": "active"
        })
        if existing:
            raise HTTPException(status_code=400, detail="Vehicle already allocated for this date")

        # Get pre-assigned driver
        driver = await database.drivers.find_one({"assigned_vehicle_id": allocation.vehicle_id})
        if not driver:
            raise HTTPException(status_code=404, detail="No driver assigned to vehicle")

        # Create allocation document
        now = datetime.utcnow()
        allocation_data = {
            "employee_id": allocation.employee_id,
            "vehicle_id": allocation.vehicle_id,
            "driver_id": driver["driver_id"],
            "allocation_date": allocation_date,
            "status": allocation.status,
            "created_at": now,
            "updated_at": now
        }

        # Insert into database
        result = await database.allocations.insert_one(allocation_data)
        
        # Prepare response
        response_data = {
            "allocation_id": str(result.inserted_id),
            **allocation_data
        }
        
        return AllocationResponse(**response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.put("/allocations/{allocation_id}", response_model=AllocationResponse)
async def update_allocation(allocation_id: str, allocation_update: AllocationUpdate):
    try:
        # Validate the allocation ID format
        allocation_object_id = ObjectId(allocation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid allocation ID format")
    
    # Fetch the existing allocation with joined data
    pipeline = [
        {"$match": {"_id": allocation_object_id}},
        {
            "$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }
        },
        {
            "$lookup": {
                "from": "vehicles",
                "localField": "vehicle_id",
                "foreignField": "vehicle_id",
                "as": "vehicle"
            }
        },
        {
            "$lookup": {
                "from": "drivers",
                "localField": "driver_id",
                "foreignField": "driver_id",
                "as": "driver"
            }
        }
    ]
    
    allocation_cursor = database.allocations.aggregate(pipeline)
    allocation = await allocation_cursor.next()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    # Check if the existing allocation date is in the past
    current_date = datetime.utcnow().date()
    allocation_date = allocation["allocation_date"].date() if isinstance(allocation["allocation_date"], datetime) else allocation["allocation_date"]
    
    if allocation_date < current_date:
        raise HTTPException(status_code=400, detail="Cannot modify past allocations")
    
    # Build update document
    update_data = {"updated_at": datetime.utcnow()}
    
    if allocation_update.status is not None:
        update_data["status"] = allocation_update.status
    
    if allocation_update.allocation_date is not None:
        # Validate new date
        if allocation_update.allocation_date < current_date:
            raise HTTPException(status_code=400, detail="Cannot allocate vehicle for past dates")
        
        # Convert date to datetime for storage
        new_allocation_date = datetime.combine(allocation_update.allocation_date, datetime.min.time())
        
        # Check vehicle availability for new date
        existing = await database.allocations.find_one({
            "vehicle_id": allocation["vehicle_id"],
            "allocation_date": new_allocation_date,
            "status": "active",
            "_id": {"$ne": allocation_object_id}
        })
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Vehicle already allocated for this date"
            )
        
        update_data["allocation_date"] = new_allocation_date
    
    # Update the allocation
    result = await database.allocations.update_one(
        {"_id": allocation_object_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Update failed")
    
    # Fetch updated allocation with joined data
    updated_allocation = await database.allocations.aggregate(pipeline).next()
    
    # Prepare response
    response_data = {
        "allocation_id": str(updated_allocation["_id"]),
        "employee_id": updated_allocation["employee_id"],
        "vehicle_id": updated_allocation["vehicle_id"],
        "driver_id": updated_allocation.get("driver_id"),
        "allocation_date": updated_allocation["allocation_date"],
        "status": updated_allocation["status"],
        "created_at": updated_allocation["created_at"],
        "updated_at": updated_allocation["updated_at"],
        "employee_name": updated_allocation["employee"][0]["name"] if updated_allocation["employee"] else None,
        "vehicle_name": updated_allocation["vehicle"][0]["vehicle_name"] if updated_allocation["vehicle"] else None,
        "driver_name": updated_allocation["driver"][0]["name"] if updated_allocation["driver"] else None
    }
    
    return AllocationResponse(**response_data)

@router.delete("/allocations/{allocation_id}", response_model=dict)
async def delete_allocation(allocation_id: str):
    try:
        # Validate the allocation ID format
        allocation_object_id = ObjectId(allocation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid allocation ID format")
    
    # Fetch the allocation
    allocation = await database.allocations.find_one({"_id": allocation_object_id})
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    # Check if the allocation date is in the past
    allocation_date = allocation["allocation_date"].date() if isinstance(allocation["allocation_date"], datetime) else allocation["allocation_date"]
    if allocation_date < datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="Cannot delete past allocations")
    
    # Delete the allocation
    result = await database.allocations.delete_one({"_id": allocation_object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Delete failed")
    
    return {"message": "Allocation deleted successfully", "allocation_id": str(allocation_object_id)}
@router.get("/allocations/history", response_model=List[AllocationResponse])
async def get_allocation_history(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    employee_id: Optional[str] = Query(None),
    vehicle_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    # Initialize query dictionary
    query = {}

    # Add date filters to the query if both are provided
    if start_date and end_date:
        query["allocation_date"] = {"$gte": start_date, "$lte": end_date}

    # Add filters for employee_id, vehicle_id, and status
    if employee_id:
        query["employee_id"] = employee_id
    if vehicle_id:
        query["vehicle_id"] = vehicle_id
    if status:
        query["status"] = status

    # Use aggregation for efficient pagination and joining
    pipeline = [
        {"$match": query},
        {"$sort": {"allocation_date": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }
        },
        {
            "$lookup": {
                "from": "vehicles",
                "localField": "vehicle_id",
                "foreignField": "vehicle_id",
                "as": "vehicle"
            }
        },
        {
            "$lookup": {
                "from": "drivers",
                "localField": "driver_id",
                "foreignField": "driver_id",
                "as": "driver"
            }
        },
        {
            "$project": {
                "allocation_id": {"$toString": "$_id"},
                "employee_id": 1,  # Include employee_id
                "vehicle_id": 1,  # Include vehicle_id
                "driver_id": 1,  # Include driver_id
                "employee_name": {"$arrayElemAt": ["$employee.name", 0]},
                "vehicle_name": {"$arrayElemAt": ["$vehicle.vehicle_name", 0]},
                "driver_name": {"$arrayElemAt": ["$driver.name", 0]},
                "allocation_date": 1,
                "status": 1,
                "created_at": 1,
                "updated_at": 1
            }
        }
    ]

    # Execute aggregation pipeline
    allocations = await database.allocations.aggregate(pipeline).to_list(length=None)

    # Check if allocations were found
    if not allocations:
        raise HTTPException(status_code=404, detail="No allocation records found for the given filters.")

    return allocations