import pytest
from datetime import datetime, date, timedelta
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio
from unittest.mock import Mock, patch
from models.models import AllocationCreate, AllocationUpdate

# Test data fixtures
@pytest.fixture
def sample_employee():
    return {
        "employee_id": "EMP001",
        "name": "John Doe",
        "status": "active"
    }

@pytest.fixture
def sample_vehicle():
    return {
        "vehicle_id": "VEH001",
        "vehicle_name": "Toyota Camry",
        "status": "available"
    }

@pytest.fixture
def sample_driver():
    return {
        "driver_id": "DRV001",
        "name": "Mike Smith",
        "assigned_vehicle_id": "VEH001",
        "status": "active"
    }

@pytest.fixture
def sample_allocation():
    return {
        "_id": ObjectId(),
        "employee_id": "EMP001",
        "vehicle_id": "VEH001",
        "driver_id": "DRV001",
        "allocation_date": datetime.combine(date.today() + timedelta(days=1), datetime.min.time()),
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

# Mock database responses
@pytest_asyncio.fixture
async def mock_db():
    with patch('config.database') as mock_db:
        # Set up mock collections
        mock_db.employees = Mock()
        mock_db.vehicles = Mock()
        mock_db.drivers = Mock()
        mock_db.allocations = Mock()
        yield mock_db

# Test cases for POST /allocations
@pytest.mark.asyncio
async def test_create_allocation_success(mock_db, sample_employee, sample_vehicle, sample_driver):
    # Setup mock responses
    mock_db.employees.find_one.return_value = sample_employee
    mock_db.vehicles.find_one.return_value = sample_vehicle
    mock_db.drivers.find_one.return_value = sample_driver
    mock_db.allocations.find_one.return_value = None
    mock_db.allocations.insert_one.return_value = Mock(inserted_id=ObjectId())

    # Create test data
    allocation_data = AllocationCreate(
        employee_id="EMP001",
        vehicle_id="VEH001",
        allocation_date=date.today() + timedelta(days=1)
    )

    async with AsyncClient() as client:
        response = await client.post("/allocations", json=allocation_data.dict())
        
    assert response.status_code == 200
    assert response.json()["employee_id"] == "EMP001"
    assert response.json()["vehicle_id"] == "VEH001"
    assert response.json()["status"] == "active"

@pytest.mark.asyncio
async def test_create_allocation_employee_not_found(mock_db):
    mock_db.employees.find_one.return_value = None

    allocation_data = AllocationCreate(
        employee_id="INVALID",
        vehicle_id="VEH001",
        allocation_date=date.today() + timedelta(days=1)
    )

    async with AsyncClient() as client:
        response = await client.post("/allocations", json=allocation_data.dict())
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"

# Test cases for PUT /allocations/{allocation_id}
@pytest.mark.asyncio
async def test_update_allocation_success(mock_db, sample_allocation):
    # Setup mock responses
    mock_db.allocations.aggregate.return_value.next.return_value = sample_allocation
    mock_db.allocations.find_one.return_value = None
    mock_db.allocations.update_one.return_value = Mock(modified_count=1)

    update_data = AllocationUpdate(
        allocation_date=date.today() + timedelta(days=2),
        status="completed"
    )

    async with AsyncClient() as client:
        response = await client.put(
            f"/allocations/{str(sample_allocation['_id'])}",
            json=update_data.dict(exclude_none=True)
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_update_allocation_not_found(mock_db):
    mock_db.allocations.aggregate.return_value.next.return_value = None

    update_data = AllocationUpdate(status="completed")

    async with AsyncClient() as client:
        response = await client.put(
            f"/allocations/{str(ObjectId())}",
            json=update_data.dict(exclude_none=True)
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Allocation not found"

# Test cases for DELETE /allocations/{allocation_id}
@pytest.mark.asyncio
async def test_delete_allocation_success(mock_db, sample_allocation):
    mock_db.allocations.find_one.return_value = sample_allocation
    mock_db.allocations.delete_one.return_value = Mock(deleted_count=1)

    async with AsyncClient() as client:
        response = await client.delete(f"/allocations/{str(sample_allocation['_id'])}")

    assert response.status_code == 200
    assert response.json()["message"] == "Allocation deleted successfully"

@pytest.mark.asyncio
async def test_delete_allocation_past_date(mock_db):
    past_allocation = {
        "_id": ObjectId(),
        "allocation_date": datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    }
    mock_db.allocations.find_one.return_value = past_allocation

    async with AsyncClient() as client:
        response = await client.delete(f"/allocations/{str(past_allocation['_id'])}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete past allocations"

# Test cases for GET /allocations/history
@pytest.mark.asyncio
async def test_get_allocation_history_success(mock_db, sample_allocation):
    mock_db.allocations.aggregate.return_value.to_list.return_value = [sample_allocation]

    async with AsyncClient() as client:
        response = await client.get("/allocations/history")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["employee_id"] == sample_allocation["employee_id"]

@pytest.mark.asyncio
async def test_get_allocation_history_with_filters(mock_db):
    mock_db.allocations.aggregate.return_value.to_list.return_value = []

    params = {
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=7)).isoformat(),
        "employee_id": "EMP001",
        "vehicle_id": "VEH001",
        "status": "active"
    }

    async with AsyncClient() as client:
        response = await client.get("/allocations/history", params=params)

    assert response.status_code == 404
    assert response.json()["detail"] == "No allocation records found for the given filters."