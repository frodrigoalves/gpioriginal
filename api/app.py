import os, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import generativeai as genai

app = Flask(__name__)
FRONT_ORIGIN = os.getenv("FRONT_ORIGIN", "http://localhost:3000")
CORS(app, resources={r"/api/*": {"origins": [FRONT_ORIGIN]}})

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Defina GOOGLE_API_KEY ou GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

@app.get("/healthz")
def health(): return {"ok": True, "ts": int(time.time())}

@app.post("/api/prescricao")
def prescricao():
    d = request.get_json(force=True)
    prompt = f"Gerar prescrição baseada em evidências. Diagnóstico: {d.get('diagnostico','')}"
    r = model.generate_content(prompt)
    return jsonify({"text": r.text, "ts": int(time.time())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
