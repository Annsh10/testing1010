# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
import os, re, json, io
from google import genai
from google.genai import types
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from dotenv import load_dotenv

# Load environment variables (for GEMINI_API_KEY)
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecret"  # change in production

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ---------------- Utility Functions ---------------- #

# Build structured prompt
def build_prompt(age, skin_type, goals, other):
    goals_text = ", ".join(goals) if goals else "none"
    return f"""
You are an expert dermatologist assistant. Generate a personalized skincare plan.

INPUT:
- Age: {age}
- Skin type: {skin_type}
- Goals: {goals_text}
- Other concerns: {other}

TASK:
Return a VALID JSON object only (no markdown, no ###, no explanations).
Schema:

{{
 "skin_analysis": "short paragraph",
 "morning_routine": ["Step 1...", "Step 2..."],
 "evening_routine": ["Step 1...", "Step 2..."],
 "diet_tips": ["Tip 1...", "Tip 2..."],
 "lifestyle": ["Tip 1...", "Tip 2..."]
}}

RULES:
- Write bullet points as plain strings (no *, -, #, or markdown).
- Keep steps concise, professional, and realistic.
- No brand names.
- If any severe condition appears, add 'consult a dermatologist' in analysis.
- JSON must strictly follow schema above.
"""

# Clean messy characters
def clean_text(s: str) -> str:
    if not isinstance(s, str):
        return s
    return re.sub(r'[#*`]+', '', s).strip()

def clean_json(plan: dict) -> dict:
    for k, v in plan.items():
        if isinstance(v, str):
            plan[k] = clean_text(v)
        elif isinstance(v, list):
            plan[k] = [clean_text(i) for i in v]
    return plan

# Call Gemini API
def call_gemini(prompt_text):
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    )
    return getattr(resp, "text", None)

# Parse JSON safely
def parse_json_from_text(text):
    if not text:
        return {"error": "No response"}
    m = re.search(r'(\{[\s\S]*\})', text)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            return {"error": "Invalid JSON", "raw": text[:200]}
    return {"error": "No JSON found", "raw": text[:200]}

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    prompt = build_prompt(
        data.get("age"),
        data.get("skin_type"),
        data.get("goals", []),
        data.get("other", "")
    )
    raw = call_gemini(prompt)
    plan = parse_json_from_text(raw)
    plan = clean_json(plan)
    session['plan'] = plan
    return jsonify({"redirect": url_for('result_page')})

@app.route('/result')
def result_page():
    return render_template('result.html', plan=session.get('plan', {}))

@app.route('/download')
def download_pdf():
    plan = session.get('plan', {})
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    def add_section(title, content):
        story.append(Paragraph(f"<b>{title}</b>", styles['Heading2']))
        if isinstance(content, list):
            for item in content:
                story.append(Paragraph("• " + item, styles['Normal']))
        else:
            story.append(Paragraph(content, styles['Normal']))
        story.append(Spacer(1, 12))

    add_section("Skin Analysis", plan.get("skin_analysis", ""))
    add_section("Morning Routine", plan.get("morning_routine", []))
    add_section("Evening Routine", plan.get("evening_routine", []))
    add_section("Diet Tips", plan.get("diet_tips", []))
    add_section("Lifestyle", plan.get("lifestyle", []))

    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="skincare_plan.pdf",
        mimetype="application/pdf"
    )

# ---------------- Run ---------------- #
if __name__ == '__main__':
    app.run(debug=True)
