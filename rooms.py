import random
import string

rooms = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_room():
    code = generate_code()

    rooms[code] = {
        "players": {"A": None, "B": None},
        "teams": {"A": [None]*6, "B": [None]*6},
        "phase": "WAITING",
        "current_team": None,
        "pending_draw": None,
        "used": set()
    }

    return code