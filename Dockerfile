# Use official Python base image
FROM python:3.12-slim

# Set the working directory
 
WORKDIR /app

# Install required Linux packages including LibreOffice and ODBC Driver 18
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    libpq-dev \
    curl \
    gnupg2 \
    libreoffice \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up ODBC drivers (Optional)
ENV ODBCINI=/etc/odbc.ini
ENV ODBCSYSINI=/etc
ENV LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:/opt/microsoft/msodbcsql18/lib

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
