
def calculate_rank_clicker(clicker: list, data_dir: str) -> None:

    clicker_new = sorted(clicker, key=lambda i: i["Clicks"])  # type: ignore
    clicker_new.reverse()

    rank = 0
    score = 1000000 * 1000000  # Assez bien oui!
    inc = 1
    final_results = []
    for result in clicker_new:
        if result["Clicks"] < score:
            score = result["Clicks"]
            rank += inc
            inc = 1
        else:
            inc += 1
        res = dict(rank=rank, Players=result["Players"], Clicks=result["Clicks"])
        final_results.append(res)
    dont_update_ranks = True
    for player in final_results:
        for initplayer in clicker:
            if player.get("Players") == initplayer.get("Players"):
                if player.get("rank") != initplayer.get("rank"):
                    dont_update_ranks = False
                    break
                continue
    if dont_update_ranks:
        print("don'tupdate")
        final_results = clicker
    with open(f"{data_dir}/teams/Clicker.json", "w") as file:
        json.dump(final_results, file)


def rm_players_from_his_pizza_list(data_dir: str) -> None:
    for player in players_list():
        overwrite = False
        with open(f"{data_dir}/teams/Pizza/{player}.json", "r") as rfile:
            print(player)
            teams = json.load(rfile)["Series"][0]["Teams"]
            for team in teams:
                if player in team["Players"]:
                    teams.remove(team)
                    overwrite = True
                    break
        if overwrite:
            with open(f"{data_dir}/teams/Pizza/{player}.json", "w") as wfile:
                aaa = dict(
                    Series=[dict(Name="Final", Teams=teams, Selected=0, NextSerie="")]
                )
                json.dump(aaa, wfile)


def trigger_tas_dhommes(match: Any, username: str, data_dir: str) -> None:
    for result in match:
        if username in result["username"] and result["rank"] == 1:
            send_notif(
                "all",
                "Tas d'hommes!",
                f"Sur {username}\nPour avoir voté pour sa propre pizza",
                data_dir,
            )
