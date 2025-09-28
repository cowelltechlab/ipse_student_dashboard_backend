import loader  # Loads all environment variables from correct .env file

from application.app import application as app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
