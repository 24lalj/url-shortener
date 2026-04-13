import hashlib
import redis
import validators
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Scalability Feature: CORS enabled for cross-environment communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Intelligent Layer: Redis Connection (Railway Internal DNS)
# host='redis' matches the service name in your docker-compose.yml
try:
    cache = redis.Redis(host='redis', port=6379, decode_responses=True)
except Exception:
    print("Redis not connected. Ensure the Redis service is running in Railway.")

# Intelligent Layer: Spam Detection Keywords
SPAM_KEYWORDS = ["free", "win", "money", "prize", "gift", "claim", "offer"]

def is_spam(url: str) -> bool:
    return any(keyword in url.lower() for keyword in SPAM_KEYWORDS)

def generate_smart_code(url: str) -> str:
    clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    keyword = clean_url.split('.')[0] 
    unique_suffix = hashlib.md5(url.encode()).hexdigest()[:4]
    return f"{keyword}-{unique_suffix}"

# --- ROUTES ---

@app.get("/")
async def read_index():
    # Force the server to find the HTML file inside the Docker container
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "index.html not found. Ensure it is in the same folder as main.py"}

@app.post("/shorten")
async def shorten_url(long_url: str, request: Request):
    if not validators.url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    spam_detected = is_spam(long_url)
    
    # PRODUCTION LOGIC: Automatically detects your .up.railway.app domain
    base_url = str(request.base_url)

    # Check Cache (Scalability)
    cached_code = cache.get(f"url:{long_url}")
    if cached_code:
        return {"short_url": f"{base_url}{cached_code}", "is_spam": spam_detected}

    # Generate and Store
    short_code = generate_smart_code(long_url)
    cache.set(short_code, long_url)
    cache.set(f"url:{long_url}", short_code)

    return {"short_url": f"{base_url}{short_code}", "is_spam": spam_detected}

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    original_url = cache.get(short_code)
    if original_url:
        return RedirectResponse(url=original_url)
    raise HTTPException(status_code=404, detail="URL not found")

# --- RAILWAY DEPLOYMENT LOGIC ---
if __name__ == "__main__":
    # Railway passes a dynamic PORT; this line captures it.
    port = int(os.environ.get("PORT", 8000))
    # host="0.0.0.0" is required to accept outside traffic
    uvicorn.run(app, host="0.0.0.0", port=port)
