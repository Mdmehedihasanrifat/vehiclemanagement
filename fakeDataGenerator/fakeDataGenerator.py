import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from faker import Faker
from pymongo.errors import BulkWriteError

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
client = AsyncIOMotorClient(MONGODB_URL)

# Check if the connection is successful
async def check_connection():
    try:
        # Attempt to get a list of databases
        await client.admin.command('ping')
        logging.info("Connected to MongoDB successfully!")
    except Exception as e:
        logging.error("Failed to connect to MongoDB:", e)

database = client['vehicle_allocation']  # Database name

# Collections
employees_collection = database['employees']
vehicles_collection = database['vehicles']
drivers_collection = database['drivers']

# Initialize Faker
fake = Faker()

# Define the number of records you want to generate
NUM_EMPLOYEES = 1000
NUM_VEHICLES = 1000
NUM_DRIVERS = 1000

# Generate fake Employees
def generate_fake_employees(num_employees):
    employees = []
    existing_ids = set()  # Track existing IDs to avoid duplicates
    while len(employees) < num_employees:
        employee_id = fake.unique.bothify(text="EMP####")
        if employee_id not in existing_ids:  # Check for uniqueness
            employee = {
                "employee_id": employee_id,
                "name": fake.name(),
                "department": fake.random_element(elements=("Engineering", "Marketing", "Finance", "Sales", "Operations", "Legal", "Human Resources", "Customer Support")),
                "contact_number": fake.phone_number()
            }
            employees.append(employee)
            existing_ids.add(employee_id)  # Add the ID to the set
    return employees

# Generate fake Vehicles
def generate_fake_vehicles(num_vehicles, drivers):
    vehicles = []
    for i in range(num_vehicles):
        vehicle = {
            "vehicle_id": fake.unique.bothify(text="VEH#####"),
            "vehicle_name": fake.company() + " " + fake.word().capitalize(),
            "driver_id": drivers[i]["driver_id"],
            "status": fake.random_element(elements=("available", "maintenance", "retired"))
        }
        vehicles.append(vehicle)
    return vehicles

# Generate fake Drivers
def generate_fake_drivers(num_drivers):
    drivers = []
    for _ in range(num_drivers):
        driver = {
            "driver_id": fake.unique.bothify(text="DRV####"),
            "name": fake.name(),
            "contact_number": fake.phone_number(),
            "license_number": fake.unique.bothify(text="LIC########"),
            "assigned_vehicle_id": None  # will be assigned later
        }
        drivers.append(driver)
    return drivers

# Assign drivers to vehicles and return all generated data
def generate_fake_data():
    drivers = generate_fake_drivers(NUM_DRIVERS)
    vehicles = generate_fake_vehicles(NUM_VEHICLES, drivers)
    employees = generate_fake_employees(NUM_EMPLOYEES)
    
    # Assign each driver to a vehicle
    for i in range(len(drivers)):
        drivers[i]["assigned_vehicle_id"] = vehicles[i]["vehicle_id"]

    return {
        "employees": employees,
        "vehicles": vehicles,
        "drivers": drivers
    }

# Function to insert data into MongoDB asynchronously
async def insert_data_into_mongodb():
    # Generate fake data
    data = generate_fake_data()

    try:
        # Clear existing collections (optional)
        await employees_collection.delete_many({})
        await vehicles_collection.delete_many({})
        await drivers_collection.delete_many({})

        # Insert employees, vehicles, and drivers into MongoDB collections
        result_employees = await employees_collection.insert_many(data['employees'])
        result_vehicles = await vehicles_collection.insert_many(data['vehicles'])
        result_drivers = await drivers_collection.insert_many(data['drivers'])

        logging.info("Data inserted successfully into MongoDB!")
        logging.info(f"Inserted Employees: {len(result_employees.inserted_ids)}")
        logging.info(f"Inserted Vehicles: {len(result_vehicles.inserted_ids)}")
        logging.info(f"Inserted Drivers: {len(result_drivers.inserted_ids)}")

    except BulkWriteError as bwe:
        logging.error("Bulk write error occurred:", bwe.details)
    except Exception as e:
        logging.error("An error occurred while inserting data:", e)

# Create indexes for optimization
async def create_indexes():
    try:
        await employees_collection.create_index("employee_id", unique=True)
        await vehicles_collection.create_index("vehicle_id", unique=True)
        await drivers_collection.create_index("driver_id", unique=True)
    except Exception as e:
        logging.error("An error occurred while creating indexes:", e)

# Main function to run the tasks
async def main():
    await check_connection()  # Check the MongoDB connection
    await create_indexes()
    await insert_data_into_mongodb()

# Run the async main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
