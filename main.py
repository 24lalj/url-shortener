import hashlib
import redis
import validators
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis Connection
cache = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.get("/")
async def read_index():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(file_path)

@app.post("/shorten")
async def shorten_url(long_url: str, request: Request):
    if not validators.url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    base_url = str(request.base_url)
    short_code = hashlib.md5(long_url.encode()).hexdigest()[:6]
    cache.set(short_code, long_url)
    return {"short_url": f"{base_url}{short_code}"}

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    url = cache.get(short_code)
    if url:
        return RedirectResponse(url=url)
    raise HTTPException(status_code=404)

# ADD THIS PART AT THE BOTTOM
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
