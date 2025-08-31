from typing import Union
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import Response

from agents.utils.portfolio import PortfolioManager

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/trades/{trade_id}")
def read_trade(trade_id: int, q: Union[str, None] = None):
    return {"trade_id": trade_id, "q": q}


@app.get("/markets/{market_id}")
def read_market(market_id: int, q: Union[str, None] = None):
    return {"market_id": market_id, "q": q}


# post new prompt

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/portfolio")
def portfolio():
    pm = PortfolioManager()
    return {
        "balance": pm.get_balance(),
        "positions": pm.get_positions(),
    }
