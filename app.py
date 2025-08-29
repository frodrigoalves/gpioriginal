import os, time, logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONT_ORIGIN", "*")}})

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, ts=int(time.time()))

@app.get("/")
def root():
    return jsonify(service="gpi-api", ok=True, endpoints=["/healthz", "POST /api/prescricao"])

def _get_model():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("API key ausente (defina GOOGLE_API_KEY ou GEMINI_API_KEY).")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return genai.GenerativeModel(model_name)

@app.post("/api/prescricao")
def prescricao():
    try:
        data = request.get_json(force=True, silent=True) or {}
        diagnostico = (data.get("diagnostico") or "").strip()
        if not diagnostico:
            return jsonify(error="Campo 'diagnostico' é obrigatório."), 400

        model = _get_model()
        prompt = (
            "Gere uma prescrição baseada em evidências (Brasil). "
            f"Diagnóstico: {diagnostico}. "
            "Retorne somente o texto: fármaco(s), dose, via, frequência, duração, "
            "cuidados/contraindicações, orientação ao paciente."
        )

        resp = model.generate_content(prompt)

        if not getattr(resp, "text", None):
            app.logger.warning("Resposta sem texto. feedback=%s candidates=%s",
                               getattr(resp, "prompt_feedback", None),
                               getattr(resp, "candidates", None))
            return jsonify(error="Resposta vazia do modelo.",
                           finish=str(getattr(resp, "prompt_feedback", ""))), 502

        return jsonify(text=resp.text, ts=int(time.time()))

    except Exception as e:
        app.logger.exception("Falha em /api/prescricao: %s", e)
        return jsonify(error="internal_error", detail=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
