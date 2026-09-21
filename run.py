"""
DBPTBS - Convenience runner for the FastAPI backend.

    python run.py

Then, in a second terminal, start the dashboard:

    streamlit run dashboard.py

(They are two separate processes; the dashboard talks directly to the
shared engine module rather than over HTTP, so it works even if you only
ever run the dashboard and skip the API - but both are provided since the
API is part of the required architecture.)
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
