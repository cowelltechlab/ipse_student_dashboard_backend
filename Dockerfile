# Use an official Python runtime as a parent image
FROM python:3.9-slim
# Install curl – Necessary for ODBC Driver installation command
RUN apt-get update && apt-get install -y curl
# Set the working directory to /app
WORKDIR /app
# Copy only the requirements file initially to leverage Docker cache
COPY requirements.txt .
# Create and activate a virtual environment
RUN python -m venv venv && \
    . venv/bin/activate
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Install ODBC driver for SQL Server
RUN apt-get update && \
    apt-get install -y gnupg2 && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list >/etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# Copy the rest of the application code into the container at /app
COPY . .
# Make port 8000 available to the world outside this container
# Note that this does not actually expose the port – it’s more of a documentation
# to let users know what port the application should be running on
EXPOSE 8000

# Add command to print current directory
RUN pwd

# Run main.py when the container launches
CMD ["python", "main.py"]