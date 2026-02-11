roles = ["Captain","Vice","Tank","Healer","Support1","Support2"]

def judge_teams(teamA, teamB):
    rounds = []
    scoreA = 0
    scoreB = 0

    for i in range(6):
        a = teamA[i]
        b = teamB[i]

        if a["power"] > b["power"]:
            winner = "A"
            scoreA += 1
        elif b["power"] > a["power"]:
            winner = "B"
            scoreB += 1
        else:
            winner = "Draw"

        rounds.append({
            "role": roles[i],
            "winner": winner
        })

    if scoreA > scoreB:
        final = "A"
    elif scoreB > scoreA:
        final = "B"
    else:
        final = "Draw"

    return {
        "rounds": rounds,
        "final_winner": final
    }