from pydantic import BaseModel

class SymbolRequest(BaseModel):
    symbol: str

class TradeRequest(BaseModel):
    symbol: str
    qty: int
    side: str