# IPSE Student Dashboard Backend
==============================

A FastAPI backend service for managing student data and interactions within the IPSE project.

## Installation
------------

1. Create a virtual environment:

   - Windows:
     py -m venv venv

   - macOS/Linux:
     python3 -m venv venv

2. Activate the virtual environment:

   - Windows (Command Prompt):
     venv\Scripts\activate

   - Windows (PowerShell):
     .\venv\Scripts\Activate.ps1

   - macOS/Linux:
     source venv/bin/activate

3. Navigate to the root of the repository if needed:
   cd ../.. (if you were inside the venv folder)

4. Install dependencies:
   pip install -r requirements.txt

## Running the Application
-----------------------

Start the FastAPI backend server:

   - Windows:
     py main.py

   - macOS/Linux:
     python3 main.py

The server will run at http://localhost:8000 by default.

To view the auto-generated API documentation, open:

   http://localhost:8000/docs

You can also start the app using your debugger by launching main.py directly.

Environment Variables & Secrets
-------------------------------

This project can load configuration values from either a `.env` file or Azure Key Vault.

Make sure to set up the following secrets or environment variables if using Azure:
- API keys
- Database connection string
- JWT secrets

Refer to the `config.py` and `secret_manager.py` files for implementation details.

