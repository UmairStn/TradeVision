# pyrefly: ignore [missing-import]
from fastapi import FastAPI

app = FastAPI(title="SmartInvestor-Lanka API")

@app.get("/")
def read_root():
    return {"status": "online", "system": "SmartInvestor-Lanka"}
