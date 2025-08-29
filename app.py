import os, time, logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from werkzeug.exceptions import HTTPException

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("gpi-api")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONT_ORIGIN", "*")}})

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, ts=int(time.time()))

# NÃO vaza segredos; só indica presença de chave
@app.get("/debug/config")
def debug_config():
    has_key = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    return jsonify(has_api_key=has_key, model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

@app.get("/")
def root():
    return jsonify(service="gpi-api", ok=True, endpoints=["/healthz","/debug/config","POST /api/prescricao"])

def get_model():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("missing_api_key: defina GOOGLE_API_KEY ou GEMINI_API_KEY no ambiente do Render.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return genai.GenerativeModel(model_name)

@app.post("/api/prescricao")
def prescricao():
    data = request.get_json(force=True, silent=True) or {}
    diagnostico = (data.get("diagnostico") or "").strip()
    if not diagnostico:
        return jsonify(error="bad_request", detail="Campo 'diagnostico' é obrigatório."), 400

    model = get_model()
    prompt = (
        "Gere uma prescrição baseada em evidências (Brasil). "
        f"Diagnóstico: {diagnostico}. "
        "Retorne somente o texto: fármaco(s), dose, via, frequência, duração, "
        "cuidados/contraindicações, orientação ao paciente."
    )
    resp = model.generate_content(prompt)
    text = getattr(resp, "text", None)
    if not text:
        return jsonify(error="upstream_empty",
                       info=str(getattr(resp, "prompt_feedback", ""))), 502
    return jsonify(text=text, ts=int(time.time()))

# Handler global: SEMPRE retorna JSON (nada de HTML 500)
@app.errorhandler(Exception)
def handle_any_error(e):
    if isinstance(e, HTTPException):
        log.warning("HTTPException %s: %s", e.code, e)
        return jsonify(error=e.name, detail=str(e)), e.code
    log.exception("Unhandled error: %s", e)
    msg = str(e)
    if "missing_api_key" in msg:
        return jsonify(error="missing_api_key", detail=msg), 500
    return jsonify(error="internal_error", detail=msg), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
