from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from groq import Groq
import json
import re
import os

# ─────────────────────────────────────────────────────
# FLASK SETUP — serves both API and frontend
# ─────────────────────────────────────────────────────

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")  # ← Replace with your key
MODEL        = "llama-3.3-70b-versatile"
client       = Groq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────────────────
# STATE MAPPINGS
# ─────────────────────────────────────────────────────

STATE_NAME_TO_CODE = {
    "MP": "MP", "MH": "MH", "DL": "DL", "KA": "KA",
    "TN": "TN", "UP": "UP", "GJ": "GJ", "RJ": "RJ",
    "AP": "AP", "TS": "TS",
    "Madhya Pradesh":  "MP",
    "Maharashtra":     "MH",
    "Delhi":           "DL",
    "Karnataka":       "KA",
    "Tamil Nadu":      "TN",
    "Uttar Pradesh":   "UP",
    "Gujarat":         "GJ",
    "Rajasthan":       "RJ",
    "Andhra Pradesh":  "AP",
    "Telangana":       "TS",
}

STATE_CODE_TO_NAME = {
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "DL": "Delhi",
    "KA": "Karnataka",
    "TN": "Tamil Nadu",
    "UP": "Uttar Pradesh",
    "GJ": "Gujarat",
    "RJ": "Rajasthan",
    "AP": "Andhra Pradesh",
    "TS": "Telangana",
}

def normalize_state(state_input):
    return STATE_NAME_TO_CODE.get(state_input, state_input)


# ─────────────────────────────────────────────────────
# LOAD DATABASES
# ─────────────────────────────────────────────────────

DATA_DIR = os.path.join(BASE_DIR, 'data')

try:
    with open(os.path.join(DATA_DIR, 'fines.json'), 'r', encoding='utf-8') as f:
        FINES_DATA = json.load(f)
    print(f"✅ Loaded fines.json — {len(FINES_DATA)} violations")
except FileNotFoundError:
    print("⚠️  data/fines.json not found — using empty list")
    FINES_DATA = []

try:
    with open(os.path.join(DATA_DIR, 'routes.json'), 'r', encoding='utf-8') as f:
        ROUTES_DATA = json.load(f)
    print(f"✅ Loaded routes.json — {len(ROUTES_DATA.get('routes', []))} routes")
except FileNotFoundError:
    print("⚠️  data/routes.json not found — route lookup disabled")
    ROUTES_DATA = {"routes": [], "state_speed_limits": {}}


# ─────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────

def ask_ai(system_prompt, user_message, max_tokens=1000):
    try:
        msg = client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message}
            ]
        )
        return msg.choices[0].message.content
    except Exception as e:
        print(f"Groq AI Error: {e}")
        return None


def parse_json_response(text):
    if not text:
        return None
    clean = re.sub(r'```json|```', '', text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', clean)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return None


def get_fine_for_vehicle(state_data, vehicle_type):
    vehicle_map = {
        "2wheeler":     "fine_2wheeler",
        "bike":         "fine_2wheeler",
        "scooter":      "fine_2wheeler",
        "car":          "fine_car",
        "suv":          "fine_car",
        "jeep":         "fine_car",
        "auto":         "fine_auto",
        "autorickshaw": "fine_auto",
        "taxi":         "fine_auto",
        "truck":        "fine_truck",
        "bus":          "fine_truck",
        "lorry":        "fine_truck",
        "hgv":          "fine_truck",
    }
    key = vehicle_map.get(vehicle_type.lower(), "fine_car")
    val = state_data.get(key, 0)
    return val if val is not None else 0


def find_route(origin, destination):
    for route in ROUTES_DATA.get("routes", []):
        o = route["origin"].lower()
        d = route["destination"].lower()
        if (origin.lower() in o or o in origin.lower()) and \
           (destination.lower() in d or d in destination.lower()):
            return route
        if (destination.lower() in o or o in destination.lower()) and \
           (origin.lower() in d or d in origin.lower()):
            return route
    return None


# ─────────────────────────────────────────────────────
# FRONTEND ROUTES
# ─────────────────────────────────────────────────────




# ─────────────────────────────────────────────────────
# API ROUTE — Health Check
# ─────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def home():
    return jsonify({
        "status":     "DriveLegal API is running",
        "version":    "2.0",
        "violations": len(FINES_DATA),
        "routes":     len(ROUTES_DATA.get("routes", [])),
        "endpoints":  [
            "POST /api/chat",
            "POST /api/validate-challan",
            "POST /api/route-briefing",
            "POST /api/calculate",
            "POST /api/cop-mode",
            "GET  /api/violations",
            "GET  /api/states",
            "GET  /api/routes",
        ]
    })


# ─────────────────────────────────────────────────────
# API ROUTE — AI Chatbot
# ─────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    user_message = data.get('message', '').strip()
    state_code   = normalize_state(data.get('state', 'MP'))
    state_name   = STATE_CODE_TO_NAME.get(state_code, state_code)

    if not user_message:
        return jsonify({"error": "Message is empty"}), 400

    system_prompt = f"""
You are DriveLegal — an AI legal co-pilot for Indian drivers.
You help citizens understand traffic laws, fines, and their legal rights.

User's state: {state_name} (code: {state_code})

FINE DATABASE:
{json.dumps(FINES_DATA, indent=2)}

State codes in database: MP=Madhya Pradesh, MH=Maharashtra, DL=Delhi,
KA=Karnataka, TN=Tamil Nadu, UP=Uttar Pradesh, GJ=Gujarat, RJ=Rajasthan,
AP=Andhra Pradesh, TS=Telangana

RULES:
1. Always give exact MV Act section number
2. Always give exact fine for user's state ({state_code})
3. Mention fines for each vehicle type if relevant
4. Reply in Hindi if user writes in Hindi
5. Be concise — max 4-5 lines
6. Never guess — only use data from the database
7. For serious offences mention imprisonment risk
8. End with: "Verify at echallan.parivahan.gov.in"
    """

    response = ask_ai(system_prompt, user_message)
    if not response:
        return jsonify({"error": "AI service unavailable. Try again."}), 500

    return jsonify({
        "response":   response,
        "state_code": state_code,
        "state_name": state_name
    })


# ─────────────────────────────────────────────────────
# API ROUTE — Challan Validator
# ─────────────────────────────────────────────────────

@app.route('/api/validate-challan', methods=['POST'])
def validate_challan():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    challan_text = data.get('text', '').strip()
    state_code   = normalize_state(data.get('state', 'MP'))
    vehicle      = data.get('vehicle', 'car')

    if not challan_text:
        return jsonify({"error": "Challan text is empty"}), 400

    system_prompt = f"""
You are an expert traffic challan validator for India.
State: {STATE_CODE_TO_NAME.get(state_code, state_code)} ({state_code})
Vehicle: {vehicle}

FINE DATABASE (state codes: MP,MH,DL,KA,TN,UP,GJ,RJ,AP,TS):
{json.dumps(FINES_DATA, indent=2)}

Read the challan. Identify violation and fine charged.
Compare with legal fine for state {state_code} and vehicle {vehicle}.

Return ONLY valid raw JSON:
{{
  "violation_found": "exact violation name",
  "section": "MV Act section number",
  "charged_amount": 0,
  "legal_amount": 0,
  "is_overcharged": false,
  "overcharge_amount": 0,
  "can_contest": false,
  "verdict": "CORRECT or OVERCHARGED or UNCLEAR",
  "advice": "What the user should do next",
  "contest_procedure": "How to contest if applicable",
  "contest_window_days": 60
}}
    """

    response = ask_ai(system_prompt, f"Validate:\n{challan_text}", max_tokens=800)
    result   = parse_json_response(response)

    if not result:
        return jsonify({"error": "Could not parse challan. Try again.", "raw": response}), 500

    return jsonify(result)


# ─────────────────────────────────────────────────────
# API ROUTE — Route Legal Briefing
# ─────────────────────────────────────────────────────

@app.route('/api/route-briefing', methods=['POST'])
def route_briefing():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    origin      = data.get('origin', '').strip()
    destination = data.get('destination', '').strip()
    vehicle     = data.get('vehicle', 'car')

    if not origin or not destination:
        return jsonify({"error": "Origin and destination required"}), 400

    known_route   = find_route(origin, destination)
    route_context = json.dumps(known_route, indent=2) if known_route else "Not in database — use general knowledge"
    speed_limits  = json.dumps(ROUTES_DATA.get("state_speed_limits", {}), indent=2)

    system_prompt = f"""
You are a route legal advisor for Indian roads.
Vehicle: {vehicle}

KNOWN ROUTE DATA (use this if it matches the query):
{route_context}

STATE SPEED LIMITS:
{speed_limits}

FINE DATABASE:
{json.dumps(FINES_DATA, indent=2)}

Give complete legal briefing for {origin} to {destination} by {vehicle}.

Return ONLY valid raw JSON:
{{
  "route_states": ["MP", "MH"],
  "total_distance_approx": "600 km",
  "estimated_time": "8-9 hours",
  "states_detail": [
    {{
      "state": "MP",
      "state_full_name": "Madhya Pradesh",
      "speed_limit_2wheeler": 60,
      "speed_limit_car": 100,
      "speed_limit_truck": 80,
      "night_driving_restrictions": "None for cars",
      "key_rules": ["Helmet mandatory", "Seatbelt mandatory"],
      "top_fines": [
        {{"violation": "Overspeeding", "amount": 1000}},
        {{"violation": "No Helmet", "amount": 300}}
      ],
      "documents_needed": ["DL", "RC", "Insurance", "PUC"]
    }}
  ],
  "critical_warnings": ["MH strict drunk driving"],
  "documents_checklist": ["DL", "RC", "Insurance", "PUC"],
  "safe_driving_tips": ["Keep documents ready at borders"]
}}
    """

    response = ask_ai(system_prompt, f"{origin} to {destination} by {vehicle}", max_tokens=1500)
    result   = parse_json_response(response)

    if not result:
        return jsonify({"error": "Could not generate briefing. Try again.", "raw": response}), 500

    return jsonify(result)


# ─────────────────────────────────────────────────────
# API ROUTE — Challan Calculator
# ─────────────────────────────────────────────────────

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    violation  = data.get('violation', '').strip().lower()
    state_code = normalize_state(data.get('state', 'MP'))
    vehicle    = data.get('vehicle', 'car')
    repeat     = data.get('repeat', False)

    if not violation:
        return jsonify({"error": "Violation name required"}), 400

    matched = None
    for item in FINES_DATA:
        if (violation in item['violation'].lower() or
                violation in item.get('hindi', '').lower()):
            matched = item
            break

    if not matched:
        system_prompt = f"""
Fine database: {json.dumps(FINES_DATA, indent=2)}
Return ONLY JSON:
{{"violation":"closest name","section":"number","fine":0,"note":"explanation"}}
        """
        response = ask_ai(system_prompt, f"Fine for {violation} in {state_code} for {vehicle}?")
        result   = parse_json_response(response)
        if result:
            fine = result.get('fine', 0) or 0
            return jsonify({
                "violation": result.get('violation', violation),
                "section":   result.get('section', 'N/A'),
                "state":     state_code,
                "state_name": STATE_CODE_TO_NAME.get(state_code, state_code),
                "vehicle":   vehicle,
                "base_fine": fine,
                "repeat_offence": repeat,
                "final_fine": fine * (2 if repeat else 1),
                "can_contest": True,
                "note":      result.get('note', ''),
                "source":    "AI estimated — verify at echallan.parivahan.gov.in"
            })
        return jsonify({"error": f"Violation '{violation}' not found"}), 404

    state_data  = matched['states'].get(state_code, {})
    base_fine   = get_fine_for_vehicle(state_data, vehicle)

    if base_fine == 0 and not state_data:
        base_fine = matched.get('national_base_fine', 0) or 0

    repeat_fine = state_data.get('repeat_fine') or 0
    if repeat:
        final_fine = repeat_fine if repeat_fine > 0 else base_fine * 2
    else:
        final_fine = base_fine

    return jsonify({
        "violation":      matched['violation'],
        "hindi":          matched.get('hindi', ''),
        "section":        matched['section'],
        "state":          state_code,
        "state_name":     STATE_CODE_TO_NAME.get(state_code, state_code),
        "vehicle":        vehicle,
        "base_fine":      base_fine,
        "repeat_offence": repeat,
        "repeat_fine":    repeat_fine,
        "final_fine":     final_fine,
        "can_contest":    matched.get('contestable', True),
        "contest_days":   matched.get('contest_days', 60),
        "can_seize":      matched.get('can_seize_vehicle', False),
        "imprisonment":   state_data.get('imprisonment', 'none'),
        "verified":       state_data.get('verified', False),
        "source":         state_data.get('source', 'echallan.parivahan.gov.in'),
        "notes":          state_data.get('notes', '')
    })


# ─────────────────────────────────────────────────────
# API ROUTE — Cop Mode
# ─────────────────────────────────────────────────────

@app.route('/api/cop-mode', methods=['POST'])
def cop_mode():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    situation  = data.get('situation', '').strip()
    state_code = normalize_state(data.get('state', 'MP'))
    vehicle    = data.get('vehicle', '2wheeler')

    if not situation:
        return jsonify({"error": "Situation required"}), 400

    system_prompt = f"""
You are a real-time legal advisor. Driver stopped by police in India.
State: {STATE_CODE_TO_NAME.get(state_code, state_code)} ({state_code})
Vehicle: {vehicle}

FINE DATABASE:
{json.dumps(FINES_DATA, indent=2)}

Give IMMEDIATE, SHORT advice. User is reading this in front of the cop.

Return ONLY valid raw JSON:
{{
  "violation_detected": "most likely violation",
  "legal_fine": 0,
  "your_rights": [
    "Right to see officer ID card",
    "Right to official e-challan receipt",
    "Right to contest in court within 60 days"
  ],
  "what_to_do": [
    "Stay calm",
    "Show DL, RC, Insurance, PUC",
    "Ask for official challan receipt"
  ],
  "what_cop_can_do": "Issue challan. Seize vehicle only for serious violations.",
  "what_cop_cannot_do": "Cannot demand cash. Cannot threaten without cause.",
  "red_flags": [
    "Cash demand = bribery — note badge number",
    "No receipt = illegal collection"
  ],
  "emergency_message": "One calm reassuring sentence"
}}
    """

    response = ask_ai(system_prompt, f"Situation: {situation}", max_tokens=800)
    result   = parse_json_response(response)

    if not result:
        return jsonify({
            "violation_detected": "Unknown",
            "legal_fine": 0,
            "your_rights": [
                "Right to see officer ID card",
                "Right to official e-challan receipt",
                "Right to contest in court within 60 days"
            ],
            "what_to_do": [
                "Stay calm and be polite",
                "Show DL, RC, Insurance, PUC",
                "Ask for official challan receipt",
                "Note the officer badge number"
            ],
            "what_cop_can_do": "Issue official e-challan. Seize vehicle only for serious violations.",
            "what_cop_cannot_do": "Cannot demand cash. Cannot detain without cause.",
            "red_flags": [
                "Cash demand = bribery — note badge number",
                "No receipt = illegal — demand one"
            ],
            "emergency_message": "Stay calm — you know your rights. Only official challan is legal payment."
        })

    return jsonify(result)


# ─────────────────────────────────────────────────────
# API ROUTE — Get All Violations
# ─────────────────────────────────────────────────────

@app.route('/api/violations', methods=['GET'])
def get_violations():
    violations = [
        {
            "id":          v['id'],
            "violation":   v['violation'],
            "hindi":       v.get('hindi', ''),
            "section":     v['section'],
            "contestable": v.get('contestable', True),
            "can_seize":   v.get('can_seize_vehicle', False),
        }
        for v in FINES_DATA
    ]
    return jsonify({"count": len(violations), "violations": violations})


@app.route('/api/states', methods=['GET'])
def get_states():
    return jsonify(STATE_CODE_TO_NAME)


@app.route('/api/routes', methods=['GET'])
def get_routes():
    routes_summary = [
        {
            "id":          r['id'],
            "name":        r['name'],
            "origin":      r['origin'],
            "destination": r['destination'],
            "distance_km": r['distance_km'],
            "states":      [s['code'] for s in r.get('states', [])]
        }
        for r in ROUTES_DATA.get('routes', [])
    ]
    return jsonify({"count": len(routes_summary), "routes": routes_summary})


# ─────────────────────────────────────────────────────
# ROUTE ALIASES — short paths for frontend compatibility
# Registered AFTER all view functions, BEFORE __main__
# ─────────────────────────────────────────────────────

app.add_url_rule('/chat',             view_func=chat,             methods=['POST'], endpoint='chat_alias')
app.add_url_rule('/calculate',        view_func=calculate,        methods=['POST'], endpoint='calculate_alias')
app.add_url_rule('/validate-challan', view_func=validate_challan, methods=['POST'], endpoint='validate_alias')
app.add_url_rule('/route-briefing',   view_func=route_briefing,   methods=['POST'], endpoint='route_alias')
app.add_url_rule('/cop-mode',         view_func=cop_mode,         methods=['POST'], endpoint='copmode_alias')
app.add_url_rule('/violations',       view_func=get_violations,   methods=['GET'],  endpoint='violations_alias')


# ─────────────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "=" * 52)
    print("  🚗  DriveLegal API Server  v2.0")
    print("=" * 52)
    print(f"  Model:      {MODEL}")
    print(f"  Violations: {len(FINES_DATA)}")
    print(f"  Routes:     {len(ROUTES_DATA.get('routes', []))}")
    print(f"  Homepage:   http://localhost:5000")
    print(f"  Chatbot:    http://localhost:5000/pages/chatbot.html")
    print(f"  Scanner:    http://localhost:5000/pages/scanner.html")
    print(f"  Route:      http://localhost:5000/pages/route.html")
    print(f"  Calculator: http://localhost:5000/pages/calculator.html")
    print(f"  Cop Mode:   http://localhost:5000/pages/copmode.html")
    print("=" * 52 + "\n")
    app.run(debug=True, port=5000, host='0.0.0.0')