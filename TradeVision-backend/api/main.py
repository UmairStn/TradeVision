# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, market, prediction

app = FastAPI(
    title="SmartInvestor-Lanka API",
    description=(
        "TradeVision backend — CSE stock analysis combining FinBERT news "
        "sentiment with an XGBoost price-direction model."
    ),
    version="0.2.0",
)

# The Vite dev server runs on a different origin, so the browser blocks API calls
# without this. Ports 5173/3000 cover Vite's default and its common fallback;
# the bare hosts cover the prod frontend container, which nginx serves on port 80
# (origin "http://localhost", no port suffix).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediction.router)
app.include_router(market.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"status": "online", "system": "SmartInvestor-Lanka"}
