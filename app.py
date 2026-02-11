import json
import random
import string
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

with open("characters.json") as f:
    CHARACTERS = json.load(f)

rooms = {}
ROLES = ["Captain","Vice","Tank","Healer","Support1","Support2"]


# =========================================================
# UTIL
# =========================================================

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# CREATE ROOM
# =========================================================

@app.route("/api/create", methods=["POST"])
def create_room():
    code = generate_room_code()

    rooms[code] = {
        "players": {"A": None, "B": None},
        "teams": {"A": [None]*6, "B": [None]*6},
        "phase": "WAITING",
        "current_team": None,
        "pending_draw": None,
        "used": set(),
        "skips": {"A": 1, "B": 1},
        "swap_done": {"A": False, "B": False}
    }

    return jsonify({"room": code, "team": "A"})


# =========================================================
# JOIN ROOM
# =========================================================

@app.route("/api/join", methods=["POST"])
def join_room():
    data = request.json
    code = data.get("room")
    username = data.get("username")

    if code not in rooms:
        return jsonify({"error": "Room not found"}), 404

    room = rooms[code]

    if room["players"]["A"] is None:
        room["players"]["A"] = username
        return jsonify({"room": code, "team": "A"})

    if room["players"]["B"] is None:
        room["players"]["B"] = username
        room["phase"] = "DRAFT"
        room["current_team"] = "A"
        return jsonify({"room": code, "team": "B"})

    return jsonify({"error": "Room full"}), 400


# =========================================================
# STATE
# =========================================================

@app.route("/api/state/<room_id>/<team>")
def state(room_id, team):

    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404

    room = rooms[room_id]

    return jsonify({
        "phase": room["phase"],
        "your_turn": room["current_team"] == team,
        "your_team": room["teams"][team],
        "opponent_joined": bool(room["players"]["A"] and room["players"]["B"]),
        "skip_available": room["skips"][team] > 0,
        "players": room["players"],
        "swap_done": room["swap_done"]
    })


# =========================================================
# DRAW
# =========================================================

@app.route("/api/draw/<room_id>/<team>")
def draw_card(room_id, team):

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    if room["phase"] != "DRAFT":
        return jsonify({"error": "Not drafting"}), 403

    if room["current_team"] != team:
        return jsonify({"error": "Not your turn"}), 403

    if room["pending_draw"] is not None:
        return jsonify({"error": "Assign first"}), 403

    available = [c for c in CHARACTERS if c["name"] not in room["used"]]

    if not available:
        return jsonify({"error": "No characters left"}), 400

    char = random.choice(available)
    room["pending_draw"] = char

    return jsonify(char)


# =========================================================
# ASSIGN
# =========================================================

@app.route("/api/assign/<room_id>", methods=["POST"])
def assign(room_id):

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    data = request.json
    team = data["team"]
    slot = data["slot"]

    if room["phase"] != "DRAFT":
        return jsonify({"error": "Not drafting"}), 403

    if room["current_team"] != team:
        return jsonify({"error": "Not your turn"}), 403

    if room["pending_draw"] is None:
        return jsonify({"error": "No card drawn"}), 400

    if room["teams"][team][slot] is not None:
        return jsonify({"error": "Slot already filled"}), 400

    room["teams"][team][slot] = room["pending_draw"]
    room["used"].add(room["pending_draw"]["name"])
    room["pending_draw"] = None

    room["current_team"] = "B" if team == "A" else "A"

    if all(room["teams"]["A"]) and all(room["teams"]["B"]):
        room["phase"] = "SWAP_OPTIONAL"
        room["swap_done"] = {"A": False, "B": False}

    return jsonify({"ok": True})


# =========================================================
# SKIP DRAW
# =========================================================

@app.route("/api/skip/<room_id>/<team>", methods=["POST"])
def skip_draw(room_id, team):

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    if room["phase"] != "DRAFT":
        return jsonify({"error": "Not drafting"}), 403

    if room["current_team"] != team:
        return jsonify({"error": "Not your turn"}), 403

    if room["skips"][team] == 0:
        return jsonify({"error": "Skip already used"}), 403

    if room["pending_draw"] is None:
        return jsonify({"error": "No card to skip"}), 400

    room["pending_draw"] = None
    room["skips"][team] -= 1

    return jsonify({"ok": True})


# =========================================================
# SWAP (SYNCED)
# =========================================================

@app.route("/api/swap/<room_id>", methods=["POST"])
def swap(room_id):

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    data = request.json
    team = data["team"]
    skip = data.get("skip", False)
    slot1 = data.get("slot1")
    slot2 = data.get("slot2")

    if room["phase"] != "SWAP_OPTIONAL":
        return jsonify({"error": "Not swap phase"}), 403

    if room["swap_done"][team]:
        return jsonify({"error": "Already decided"}), 403

    if not skip:
        if slot1 is None or slot2 is None:
            return jsonify({"error": "Invalid swap"}), 400

        room["teams"][team][slot1], room["teams"][team][slot2] = \
            room["teams"][team][slot2], room["teams"][team][slot1]

    room["swap_done"][team] = True

    if room["swap_done"]["A"] and room["swap_done"]["B"]:
        room["phase"] = "RESULT"

    return jsonify({"ok": True})


# =========================================================
# RESULT
# =========================================================

@app.route("/api/result/<room_id>")
def get_result(room_id):

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    if room["phase"] != "RESULT":
        return jsonify({"error": "Game not finished"}), 403

    rounds = []
    scoreA = 0
    scoreB = 0

    for i in range(6):

        role = ROLES[i]
        a = room["teams"]["A"][i]
        b = room["teams"]["B"][i]

        a_power = a["roles"][role]
        b_power = b["roles"][role]

        a_final = int(a_power * random.uniform(0.9, 1.1))
        b_final = int(b_power * random.uniform(0.9, 1.1))

        if a_final > b_final:
            winner = room["players"]["A"]
            scoreA += 1
        elif b_final > a_final:
            winner = room["players"]["B"]
            scoreB += 1
        else:
            winner = "Draw"

        rounds.append({
            "role": role,
            "A_name": a["name"],
            "B_name": b["name"],
            "A_power": a_final,
            "B_power": b_final,
            "winner": winner
        })

    if scoreA > scoreB:
        final = room["players"]["A"]
    elif scoreB > scoreA:
        final = room["players"]["B"]
    else:
        final = "Draw"

    return jsonify({
        "rounds": rounds,
        "final_winner": final
    })


# =========================================================

if __name__ == "__main__":
    app.run(debug=True)