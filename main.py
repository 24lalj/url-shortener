import hashlib
import redis
import validators
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis Connection - matches your docker-compose service name
cache = redis.Redis(host='redis', port=6379, decode_responses=True)

# Intelligent Layer: Spam Detection
SPAM_KEYWORDS = ["free", "win", "money", "prize", "gift", "claim", "offer"]

def is_spam(url: str) -> bool:
    return any(keyword in url.lower() for keyword in SPAM_KEYWORDS)

def generate_smart_code(url: str) -> str:
    clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    keyword = clean_url.split('.')[0] 
    unique_suffix = hashlib.md5(url.encode()).hexdigest()[:4]
    return f"{keyword}-{unique_suffix}"

# --- UPDATED ROUTE TO FIX BLANK SCREEN ---
@app.get("/")
async def read_index():
    # Get the absolute path to ensure Docker finds the file
    file_path = os.path.join(os.getcwd(), "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "index.html not found in container root"}

@app.post("/shorten")
async def shorten_url(long_url: str, request: Request):
    if not validators.url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    spam_detected = is_spam(long_url)
    base_url = str(request.base_url)

    cached_code = cache.get(f"url:{long_url}")
    if cached_code:
        return {"short_url": f"{base_url}{cached_code}", "is_spam": spam_detected}

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
