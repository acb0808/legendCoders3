# Legend Coder Platform Backend

This is the backend for the Legend Coder Platform, built with FastAPI.

## Setup

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    ./venv/Scripts/activate
    # Linux/macOS
    # source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure environment variables:**
    Create a `.env` file in the `backend` directory with the following content:
    ```
    PORT=8000
    DATABASE_URL="postgresql://user:password@localhost:5432/legendcoder"
    ```
4.  **Run the application:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    The API documentation will be available at `http://localhost:8000/docs`.

---
