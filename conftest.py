import pytest, time


@pytest.fixture
def address() -> str:
    return "TEST123456789abcdefghijklmnopqrstuvwxyz"


@pytest.fixture
def prices(address: str):
    base_price = 0.001
    base_time = int(time.time())
    generated = []
    for i in range(10):
        if i < 3:
            price = base_price * (1 + (i * 0.1))
        elif i < 6:
            price = base_price * (1.5 + (i * 0.3))
        else:
            price = base_price * (2.5 + (i * 0.2))
        price *= (1 + (i * 0.05))
        high = price * 1.1
        low = price * 0.9
        open_price = price * 0.95
        close_price = price
        bar = {
            "address": address,
            "ts_start": base_time + (i * 60),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close_price,
            "volume": 1000000 + (i * 100000),
            "fdv_usd": 1000000 + (i * 100000),
            "marketcap_usd": 500000 + (i * 50000),
            "samples": 30,
        }
        generated.append(bar)
    return generated

