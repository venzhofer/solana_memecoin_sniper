import os, time, typing, requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = "https://api.rugcheck.xyz/v1"
API_KEY = os.getenv("RUGCHECK_API_KEY")

# Remove API key requirement since endpoint works without it
HEADERS = {"Accept": "application/json"}

def _req(url: str, params: typing.Optional[dict] = None) -> typing.Optional[dict]:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if r.status_code == 429:
            # rate limited: let caller retry
            print("[rugcheck] Rate limited (429)")
            return {"__rate_limited__": True}
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        if "unable to generate report" in str(e):
            # This is normal for new tokens
            return None
        print(f"[rugcheck] Request exception: {e}")
        return None

def get_risk_level(contract: str, retries: int = 2, sleep_s: float = 0.6) -> typing.Tuple[typing.Optional[int], typing.Optional[dict]]:
    """
    Returns (riskLevel, full_json) for the token. None if unavailable.
    """
    # Use the correct endpoint format: /v1/tokens/{contract}/report/summary
    url = f"{BASE_URL}/tokens/{contract}/report/summary"
    
    for i in range(retries + 1):
        data = _req(url)
        
        if data is None:
            # network/api error or new token
            if i < retries:
                time.sleep(sleep_s)
                continue
            return None, None
        if data.get("__rate_limited__"):
            if i < retries:
                time.sleep(sleep_s * (i + 1))
                continue
            return None, None
        # riskLevel may be int or nested; support common shapes
        risk = data.get("score_normalised")  # Use normalized score instead of raw score
        if risk is None:
            # fallback to raw score if normalized is not available
            risk = data.get("score")
        if risk is None:
            # some responses nest scoring; attempt trustScore.value as fallback
            ts = (data.get("trustScore") or {}).get("value")
            try:
                risk = int(ts) if ts is not None else None
            except Exception:
                risk = None
        try:
            risk = int(risk) if risk is not None else None
        except Exception:
            risk = None
        return risk, data
    
    return None, None
