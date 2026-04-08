
import os
import sys
import re
import json
import io
import uuid
import time
import secrets
import logging
import mimetypes
import uvicorn
import pathlib
import fitz  # PyMuPDF
from dotenv import load_dotenv
from fastapi import File, Path, UploadFile, HTTPException, Request, Header, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.concurrency import run_in_threadpool

env_path = pathlib.Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") 
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", 5242880))
MAX_CLAUSES = int(os.environ.get("MAX_CLAUSES", 200))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import LegalAuditorAction, LegalAuditorObservation
from server.legal_auditor_env_environment import LegalAuditorEnvironment, get_auditor
from server.oracle import evaluate_clause_difficulty_and_truth
from openenv.core.env_server.http_server import create_app

# Optional PDF generators — skip gracefully if not present
try:
    from server.pdf_generator import generate_audit_pdf
except ImportError:
    generate_audit_pdf = None   # type: ignore

try:
    from server.user_report_generator import generate_user_report_pdf
except ImportError:
    generate_user_report_pdf = None   # type: ignore

# CORS — read from env; fall back to localhost only
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:7860"
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ── Rate limiter ──────────────────────────────────────────────────────────────
_rate_store: dict = {}

async def rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/audit":
        return await call_next(request)
    client_ip   = (request.client.host if request.client else "unknown")
    current_ts  = time.time()
    last_ts, cnt = _rate_store.get(client_ip, (current_ts, 0))
    if current_ts - last_ts < 60:
        if cnt >= 50:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
        _rate_store[client_ip] = (last_ts, cnt + 1)
    else:
        _rate_store[client_ip] = (current_ts, 1)
    return await call_next(request)

# ── OpenEnv app ───────────────────────────────────────────────────────────────
app = create_app(
    env              = lambda: LegalAuditorEnvironment(),
    action_cls       = LegalAuditorAction,
    observation_cls  = LegalAuditorObservation,
    env_name         = "legal_auditor_env",
    max_concurrent_envs = 100,
)
class ForceStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".css"):
            response.headers["Content-Type"] = "text/css"
        elif path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        return response

app.middleware("http")(rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ALLOWED_ORIGINS,
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = os.path.join(current_dir, "dist")
LOG_DIR = os.path.join(current_dir, "logs") 
TRAINING_LOG_DIR = os.path.join(current_dir, "training_logs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRAINING_LOG_DIR, exist_ok=True)

app.mount("/assets", ForceStaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

# 3. Mount Logs for direct access
app.mount("/api/logs", StaticFiles(directory=LOG_DIR), name="logs")
app.mount("/api/training", StaticFiles(directory=TRAINING_LOG_DIR), name="training")

    # 3. Serve the index.html for the root path
@app.get("/", tags=["UI"])
async def serve_index():
        return FileResponse(os.path.join(dist_path, "index.html"))

    # 4. Handle SPA routing (React/Vite Router support)
   
# ── Session ID validator (path-traversal guard) ───────────────────────────────
SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9\-_]{8,64}$")

def _validate_session_id(session_id: str):
    if not SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")

# ── Session token verifier ────────────────────────────────────────────────────
async def verify_session_access(session_id: str, provided_token: str):
    # 1. Basic ID Validation
    _validate_session_id(session_id)

    # 2. File Path Construction
    pattern = f"session_{session_id}.json"
    filepath = os.path.join(LOG_DIR, pattern)
    
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        # 3. Open file to check for a stored token
        with open(filepath, "r") as f:
            data = json.load(f)
            
        # Get the token from the first entry of the log
        stored_token = data[0].get("session_token") if data else None

        # --- THE LEGACY SUPPORT LOGIC ---
        
        # CASE A: This is a legacy file (created before tokens were added).
        # There is no stored token, so we allow access to prevent data loss.
        if stored_token is None:
            return True 
            
        # CASE B: This is a secure file.
        # A token exists in the file, so the user MUST provide a matching token.
        if not provided_token or not secrets.compare_digest(provided_token, stored_token):
            raise HTTPException(
                status_code=403, 
                detail="Unauthorized: A security token is required for this session."
            )

    except HTTPException:
        # Re-raise FastAPIs HTTPExceptions so they reach the user
        raise
    except Exception as e:
        # Log the actual error for the developer, but send a generic 500 to the user
        print(f"Security Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error verifying session token.")
    
    return True
# ── Admin token guard ─────────────────────────────────────────────────────────
async def require_admin(x_admin_token: str = Header(None)):
    if ADMIN_TOKEN == "dev_secret_zoro":
        return True
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin endpoints disabled (ADMIN_TOKEN not set).")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Unauthorized.")

# ── PDF text extractor ────────────────────────────────────────────────────────
def _extract_pdf_text_sync(content: bytes) -> str:
    doc = fitz.open(stream=content, filetype="pdf")
    pages = [str(page.get_text("text")) for page in doc]
    doc.close()
    return "\n".join(pages)

# ── /audit ────────────────────────────────────────────────────────────────────
@app.post("/audit")
async def run_audit(file: UploadFile = File(...)):
    content  = await file.read()
    filename = file.filename or "uploaded_file"

    # 1. File size guard
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_BYTES} bytes.")

    auditor = get_auditor()
    auditor.start_new_session()
    session_token = secrets.token_urlsafe(32)
    auditor.session_token = session_token

    # 2. Document Parsing
    try:
        if filename.lower().endswith(".pdf"):
            full_text = await run_in_threadpool(_extract_pdf_text_sync, content)
            clauses   = [c.strip() for c in full_text.split("\n\n") if len(c.strip()) > 30]
        else:
            clauses = [
                c.strip()
                for c in content.decode("utf-8", errors="replace").split("\n")
                if len(c.strip()) > 10
            ]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Parsing error: {exc}")

    clauses = clauses[:MAX_CLAUSES]

    # 3. Dual-Data Collection
    audit_results = []   # For the User UI (logs/)
    training_data = []    # For the RL Oracle (training_logs/)

    for i, text in enumerate(clauses):
        oracle_data = evaluate_clause_difficulty_and_truth(text)
        result = auditor.audit_clause_text(text, i, oracle_data)
        
        # Prepare AI Report Data (User-Facing)
        clean_result = result.copy()
        clean_result["reward"] = round(max(0.0, min(1.0, float(clean_result.get("reward", 0.0)))), 4)
        # 🚩 CRITICAL: We keep the session_token in the first record for the verifier
        if i == 0:
            clean_result["session_token"] = session_token
        else:
            clean_result.pop("session_token", None)
            
        audit_results.append(clean_result)

        # Prepare Training Data (Internal/RL-Facing)
        training_entry = {
            "clause_index": i,
            "text": text,
            "ground_truth": oracle_data,
            "ai_action": clean_result.get("action"),
            "ai_reward": clean_result.get("reward"),
            "timestamp": time.time()
        }
        training_data.append(training_entry)

    # 4. Binary Storage Logic (Explicit Writes)
    
    # 🚩 FIX: Manually save the AI Session Log to the specific LOG_DIR
    # This bypasses any internal path defaults in the auditor object
    ai_filename = f"session_{auditor.session_id}.json"
    ai_filepath = os.path.join(LOG_DIR, ai_filename)
    
    with open(ai_filepath, "w") as f:
        json.dump(audit_results, f, indent=2)

    # Save the specialized Training Log for Oracle reports
    training_filename = f"oracle_{auditor.session_id}.json"
    training_filepath = os.path.join(TRAINING_LOG_DIR, training_filename)
    
    with open(training_filepath, "w") as f:
        json.dump(training_data, f, indent=2)

    return {
        "status":        "success",
        "session_id":    auditor.session_id,
        "session_token": session_token,
        "data":          audit_results,
    }
# ── /developer/sessions — requires ADMIN_TOKEN ────────────────────────────────
@app.get("/developer/sessions", dependencies=[Depends(require_admin)])
async def list_sessions():
    if not os.path.exists(LOG_DIR):
        return {"status": "success", "sessions": []}
        
    sessions = []
    for fname in os.listdir(LOG_DIR):
        if fname.startswith("session_") and fname.endswith(".json"):
            filepath = os.path.join(LOG_DIR, fname)
            # Use file stats instead of opening the file
            mtime = os.path.getmtime(filepath) 
            
            sessions.append({
                "session_id": fname[len("session_"):-len(".json")],
                "timestamp": mtime, # Frontend handles the conversion
                "fileName": fname.upper()
            })
            
    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"status": "success", "sessions": sessions}

# ── /stats/{session_id} ───────────────────────────────────────────────────────
@app.get("/stats/{session_id}")
async def get_session_stats(
    session_id: str,
    x_session_token: str = Header(None),
):
    await verify_session_access(session_id, x_session_token)
    filepath = os.path.join(LOG_DIR, f"session_{session_id}.json")
    with open(filepath) as f:
        data = json.load(f)

    total_clauses = len(data)
    total_reward  = sum(item.get("reward", 0.0) for item in data)
    correct = sum(
        1 for item in data
        if (item.get("action") == 1 and item.get("is_actually_risk"))
        or (item.get("action") == 0 and not item.get("is_actually_risk"))
    )
    accuracy     = (correct / total_clauses * 100) if total_clauses else 0.0
    avg_ai_grade = (
        sum(item.get("ai_grade", 0.0) for item in data) / total_clauses
        if total_clauses else 0.0
    )
    return {
        "session_id":   session_id,
        "total_reward": round(total_reward, 2),
        "accuracy":     f"{round(accuracy, 1)}%",
        "avg_ai_grade": round(avg_ai_grade, 4),
        "total_clauses": total_clauses,
        "timestamp":    data[0].get("timestamp", "unknown"),
    }

# ── /data/{session_id} ────────────────────────────────────────────────────────
@app.get("/data/{session_id}")
async def get_session_data(
    session_id: str,
    x_session_token: str = Header(None),
):
    await verify_session_access(session_id, x_session_token)
    filepath = os.path.join(LOG_DIR, f"session_{session_id}.json")
    with open(filepath) as f:
        return json.load(f)

# ── /export/report/{session_id} ───────────────────────────────────────────────
@app.get("/export/report/{session_id}")
async def export_user_report(session_id: str, x_session_token: str = Header(None)):
    await verify_session_access(session_id, x_session_token)
    
    if generate_user_report_pdf is None:
        raise HTTPException(status_code=501, detail="User report generator not found.")
    
    filepath = os.path.join(LOG_DIR, f"session_{session_id}.json")
    with open(filepath) as f:
        data = json.load(f)

    # CRITICAL: Return the bytes directly into the stream and add headers
    pdf_bytes = generate_user_report_pdf(data, session_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Legal_Analysis_{session_id}.pdf",
            "Content-Type": "application/pdf",
            "Content-Length": str(len(pdf_bytes))
        }
    )

# ── /export/{session_id} ──────────────────────────────────────────────────────
@app.get("/export/{session_id}")
async def export_oracle_pdf(session_id: str, x_session_token: str = Header(None)):
    await verify_session_access(session_id, x_session_token)
    
    if generate_audit_pdf is None:
        raise HTTPException(status_code=501, detail="Oracle PDF generator not found.")
    
    filepath = os.path.join(LOG_DIR, f"session_{session_id}.json")
    with open(filepath) as f:
        data = json.load(f)

    pdf_content = generate_audit_pdf(data, session_id)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Oracle_Audit_{session_id}.pdf",
            "Content-Type": "application/pdf",
            "Content-Length": str(len(pdf_content))
        }
    )
@app.get("/{full_path:path}", tags=["UI"])
async def serve_spa(full_path: str):
        # Prevent the UI from intercepting OpenEnv API calls
        if full_path.split('/')[0] in ["reset", "step", "state", "health"]:
             # If a path matches an API route but reached here, it's a 404 for the API
             return JSONResponse(status_code=404, content={"detail": "API route not found"})
        
        return FileResponse(os.path.join(dist_path, "index.html"))


# 4. The Final Catch-All Route
@app.get("/{catchall:path}")
async def serve_react_app(catchall: str):
    # Security: Don't let the UI "eat" API calls
    api_prefixes = ("audit", "developer", "export", "stats", "data", "reset", "step", "state", "health")
    if catchall.startswith(api_prefixes):
         return JSONResponse(status_code=404, content={"detail": "API route not found"})
         
    # Try to serve the actual file (like index-BI2ghD_z.js)
    file_path = os.path.join(dist_path, catchall)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Fallback to index.html for React Router
    return FileResponse(os.path.join(dist_path, "index.html"))
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)