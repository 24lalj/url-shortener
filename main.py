import hashlib
import redis
import validators
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS so the browser can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis Cache Layer (Scalable Component)
cache = redis.Redis(host='redis', port=6379, decode_responses=True)

# Intelligent Layer: Spam Detection Keywords
SPAM_KEYWORDS = ["free", "win", "money", "prize", "gift", "claim", "offer"]

def is_spam(url: str) -> bool:
    return any(keyword in url.lower() for keyword in SPAM_KEYWORDS)

# Intelligent Layer: Smart URL Generator
def generate_smart_code(url: str) -> str:
    clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    keyword = clean_url.split('.')[0] 
    unique_suffix = hashlib.md5(url.encode()).hexdigest()[:4]
    return f"{keyword}-{unique_suffix}"

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/shorten")
async def shorten_url(long_url: str):
    if not validators.url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # 1. Detect Spam (but don't block)
    spam_detected = is_spam(long_url)

    # 2. Check Cache
    cached_code = cache.get(f"url:{long_url}")
    if cached_code:
        return {"short_url": f"http://localhost:8000/{cached_code}", "is_spam": spam_detected}

    # 3. Generate Smart Link
    short_code = generate_smart_code(long_url)
    
    # 4. Store in Redis
    cache.set(short_code, long_url)
    cache.set(f"url:{long_url}", short_code)

    return {"short_url": f"http://localhost:8000/{short_code}", "is_spam": spam_detected}

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    original_url = cache.get(short_code)
    if original_url:
        return RedirectResponse(url=original_url)
    raise HTTPException(status_code=404, detail="URL not found")