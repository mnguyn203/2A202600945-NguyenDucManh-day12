"""
Production AI Agent — Final Project
Kết hợp: Stateless Redis, Rate Limiting, Cost Guard, Health Checks, Graceful Shutdown, API Key Auth.
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Khởi tạo kết nối Redis (lazy — không crash nếu chưa có)
# ─────────────────────────────────────────────────────────
redis_client = None

def _get_redis():
    """Lazy init Redis — chỉ kết nối khi thực sự cần."""
    global redis_client
    if redis_client is None:
        import redis
        REDIS_URL = settings.redis_url or "redis://localhost:6379"
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client

# ─────────────────────────────────────────────────────────
# ChromaDB (lazy init in lifespan)
# ─────────────────────────────────────────────────────────
chroma_client = None
chroma_collection = None

# ─────────────────────────────────────────────────────────
# Rate Limiting & Cost Guard (Redis - Stateless)
# ─────────────────────────────────────────────────────────
def check_rate_limit(user_id: str):
    """Giới hạn 10 request/phút mỗi user bằng Redis (Tạo state stateless)."""
    try:
        r = _get_redis()
        current_minute = int(time.time() // 60)
        key = f"rate_limit:{user_id}:{current_minute}"
        
        count = r.incr(key)
        if count == 1:
            r.expire(key, 60)  # Chỉ giữ key này trong 60s
            
        limit = settings.rate_limit_per_minute
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} req/min",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limit check failed (Redis unavailable): {e}")

def check_budget(user_id: str, cost: float):
    """Giới hạn $10 mỗi tháng bằng Redis."""
    try:
        r = _get_redis()
        current_month = datetime.now().strftime("%Y-%m")
        key = f"budget:{user_id}:{current_month}"
        
        current = float(r.get(key) or 0.0)
        if current + cost > settings.daily_budget_usd:
            raise HTTPException(503, "Monthly budget exhausted. Try again next month.")
            
        r.incrbyfloat(key, cost)
        r.expire(key, 32 * 24 * 3600)  # Tự động xoá sau 32 ngày
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Budget check failed (Redis unavailable): {e}")

# ─────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready, chroma_client, chroma_collection
    logger.info(json.dumps({"event": "startup", "app": settings.app_name}))
    
    # Init Redis connection
    try:
        r = _get_redis()
        r.ping()
        logger.info(json.dumps({"event": "redis_ready"}))
    except Exception as e:
        logger.warning(json.dumps({"event": "redis_unavailable", "error": str(e)}))
    
    # Init ChromaDB
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        chroma_client = chromadb.PersistentClient(path=db_path)
        emb = embedding_functions.DefaultEmbeddingFunction()
        chroma_collection = chroma_client.get_or_create_collection(
            name="day10_kb", embedding_function=emb
        )
        logger.info(json.dumps({"event": "chromadb_ready", "path": db_path}))
    except Exception as e:
        logger.warning(json.dumps({"event": "chromadb_unavailable", "error": str(e)}))
        
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))
    yield
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# Khởi tạo App
# ─────────────────────────────────────────────────────────
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class AskResponse(BaseModel):
    question: str
    answer: str
    history: list[str]
    model: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────
@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Nếu container bị đơ, orchestrator sẽ restart."""
    return {
        "status": "ok", 
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }

@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Check xem app đã sẵn sàng chưa."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    # Check Redis nếu có
    try:
        r = _get_redis()
        r.ping()
    except Exception:
        raise HTTPException(503, "Redis not available")
    return {"ready": True}

@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(body: AskRequest, _key: str = Depends(verify_api_key)):
    """API Chính của Agent có kèm theo Conversation History."""
    # Định danh user thông qua 8 ký tự đầu của API Key
    user_id = _key[:8]
    
    # 1. Rate Limiting
    check_rate_limit(user_id)
    
    # 2. Budget Check (Input)
    input_tokens = len(body.question.split()) * 2
    cost_in = (input_tokens / 1000) * 0.00015
    check_budget(user_id, cost_in)
    
    # 3. Lấy Lịch sử từ Redis
    history_key = f"history:{user_id}"
    
    # 4. Gọi Retrieval từ ChromaDB
    answer = "Không tìm thấy thông tin."
    if chroma_collection:
        try:
            res = chroma_collection.query(query_texts=[body.question], n_results=1)
            docs = (res.get("documents") or [[]])[0]
            if docs:
                answer = f"Truy xuất từ tài liệu:\n{docs[0]}"
        except Exception as e:
            logger.error(f"Chroma query error: {e}")
            answer = f"Lỗi truy xuất dữ liệu: {e}"
    else:
        answer = "Hệ thống ChromaDB chưa sẵn sàng."
    
    # 5. Budget Check (Output)
    output_tokens = len(answer.split()) * 2
    cost_out = (output_tokens / 1000) * 0.0006
    check_budget(user_id, cost_out)
    
    # 6. Lưu lịch sử vào Redis (chỉ giữ 10 dòng gần nhất)
    try:
        r = _get_redis()
        r.rpush(history_key, f"User: {body.question}")
        r.rpush(history_key, f"Agent: {answer}")
        r.ltrim(history_key, -10, -1)
        updated_history = r.lrange(history_key, 0, -1)
    except Exception as e:
        logger.warning(f"Redis history failed: {e}")
        updated_history = []
    
    return AskResponse(
        question=body.question,
        answer=answer,
        history=updated_history,
        model=settings.llm_model
    )

# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host=settings.host, 
        port=settings.port,
        timeout_graceful_shutdown=30
    )
