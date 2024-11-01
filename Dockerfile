# Use an official Python 3.12 runtime as a parent image
FROM python:3.12-slim

# Set the working directory
WORKDIR /

# Copy the current directory contents into the container at /app
COPY . /

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port 8000 to the outside world
EXPOSE 8000

# Define the command to run the FastAPI app using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
