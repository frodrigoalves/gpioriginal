import os, time, traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

# Google Generative AI (Gemini)
try:
    import google.generativeai as genai
except Exception as _imp_err:
    genai = None

app = Flask(__name__)
CORS(app)  # simples e efetivo p/ agora

MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

def _cfg_gemini():
    if not API_KEY:
        raise RuntimeError("missing_api_key")
    if genai is None:
        raise RuntimeError("google-generativeai-not-installed")
    genai.configure(api_key=API_KEY)

@app.get("/")
def root():
    return jsonify(ok=True, name="GPI API", version="1.0.0")

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, ts=int(time.time()))

@app.get("/debug/config")
def debug_config():
    return jsonify(
        has_api_key=bool(API_KEY),
        model=MODEL,
        front_origin=os.getenv("FRONT_ORIGIN"),
        mock_enabled=os.getenv("DISABLE_GEMINI") == "1",
    )

def gerar_prescricao(diagnostico: str) -> str:
    # Modo mock para isolar problemas de API/quotas/restrições
    if os.getenv("DISABLE_GEMINI") == "1":
        return f"[MOCK] Prescrição para {diagnostico}: Dipirona 500 mg VO 8/8h por 3 dias."

    _cfg_gemini()
    prompt = (
        "Você é um médico. Gere uma prescrição sucinta, baseada em evidências, "
        "com posologia, via, duração, e alertas de segurança, para o diagnóstico: "
        f"{diagnostico}. Formate como texto simples."
    )
    model = genai.GenerativeModel(MODEL)
    resp  = model.generate_content(prompt)
    if hasattr(resp, "text") and resp.text:
        return resp.text.strip()
    # Se não vier texto, expõe sumário bruto para debug
    return str(getattr(resp, "candidates", resp))

@app.post("/api/prescricao")
def api_prescricao():
    data = request.get_json(force=True, silent=True) or {}
    dx = (data.get("diagnostico") or "").strip()
    if not dx:
        return jsonify(error="invalid_request", detail="diagnostico obrigatório"), 400
    try:
        texto = gerar_prescricao(dx)
        return jsonify(diagnostico=dx, text=texto)
    except Exception as e:
        app.logger.exception("Falha em /api/prescricao")
        code = 500
        if str(e) == "missing_api_key":
            code = 400
        return jsonify(error="internal_error", detail=str(e)), code

@app.errorhandler(Exception)
def handle_any_error(e):
    app.logger.exception("Unhandled error")
    return jsonify(error="internal_error", detail=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
