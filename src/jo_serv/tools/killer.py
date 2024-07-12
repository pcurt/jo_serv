import json
from itertools import cycle
import logging
import datetime
import random
from jo_serv.tools.tools import send_notif
from jo_serv.tools.match_mgmt import add_new_results, update_global_results
from typing import Any

class AlreadyDeadError(Exception):
    pass


class AlreadyStartedError(Exception):
    pass


class NoKillerError(Exception):
    pass


class PlayerNotFoundError(Exception):
    pass


def killer_players(data_dir: str) -> list:
    with open(f"{data_dir}/athletes/All.json", "r") as file:
        data = json.load(file)
    to_return = []
    for player in data:
        if player["in_killer"]:
            to_return.append(player["Player"])
    return to_return


def switch_state_killer(data_dir: str, name: str, state: bool) -> None:
    with open(f"{data_dir}/athletes/All.json", "r") as file:
        data = json.load(file)
    for player in data:
        if player["Player"] == name:
            player["in_killer"] = state
    with open(f"{data_dir}/athletes/All.json", "w") as file:
        json.dump(data, file)


def generate_killer(data_dir: str) -> bool:
    logging.info("Starting killer")
    old_data = get_killer_data(data_dir)
    if old_data["started"]:
        logging.info("Killer already started")
        raise AlreadyStartedError
    data: dict = dict()
    data["started"] = True
    data["over"] = False
    data["arbitre"] = ["Fabien", "Bifteck"]
    data["participants"] = []
    data["start_date"] = datetime.datetime.now().timestamp()
    for player in killer_players(data_dir):
        data["participants"].append(
            {
                "name": player,
                "is_alive": True,
                "how_to_kill": "",
                "kills": [],
                "index": 0,
                "rank": 0
            }
        )

    with open(f"{data_dir}/killer/killer_missions.json", "r") as missions_file:
        missions_data = json.load(missions_file)
    if len(missions_data) < len(data["participants"]):
        missing = len(data["participants"]) - len(missions_data)
        logging.error(f"Can't start Killer: missing {missing} missions")
        return False

    missions = missions_data
    random.shuffle(missions)
    random.shuffle(data["participants"])
    for i, participant in enumerate(data["participants"]):
        participant["index"] = i
        mission = missions.pop()["title"]
        participant["how_to_kill"] = mission

    with open(f"{data_dir}/killer/killer_missions.json", "w") as missions_file:
        json.dump(missions_data, missions_file)

    save_killer_data(data_dir, data)
    return True


def compute_lifetime(time_alive: float) -> str:
    days = int(time_alive / 86400)
    hours = int(time_alive % 86400 / 3600)
    minutes = int(time_alive % 3600 / 60)
    seconds = int(time_alive % 60)
    return f"{days}j {hours}h {minutes}min {seconds}s"


def find_player_index(data_dir: str, name: str) -> Any:
    data = get_killer_data(data_dir)
    participants = data["participants"]
    for player in participants:
        if player["name"] == name:
            return player["index"]
    raise PlayerNotFoundError()


def find_killer_index(data_dir: str, player_index: int, counter_kill: bool) -> Any:
    data = get_killer_data(data_dir)
    participants = data["participants"]
    reordered_list = participants[player_index+1:] + participants[:player_index]
    if not counter_kill:
        reordered_list.reverse()
    for player in reordered_list:
        if player["is_alive"]:
            return player["index"]
    raise NoKillerError()


def get_mission(data_dir: str, player_index: int) -> str:
    data = get_killer_data(data_dir)
    participants = data["participants"]
    return participants[player_index]["how_to_kill"]


def find_victim(data_dir: str, player_index: int) -> Any:
    return find_killer_index(data_dir, player_index, True)


def get_killer_data(data_dir: str) -> Any:
    with open(f"{data_dir}/killer/killer.json", "r") as f:
        data = json.load(f)
    data["participants"] = sorted(data["participants"], key=lambda d: d["index"])  # type: ignore
    return data


def save_killer_data(data_dir: str, data: dict) -> None:
    with open(f"{data_dir}/killer/killer.json", "w") as f:
        json.dump(data, f)


def kill_player(data_dir: str, index: int) -> dict:
    data = get_killer_data(data_dir)
    name = data["participants"][index]["name"]
    logging.info(f"Trying to kill {name}")
    rank = count_still_alive(data_dir)
    if data["participants"][index]["is_alive"] is False:
        logging.info(f"Player: {name} is already dead")
        raise AlreadyDeadError()

    data["participants"][index]["is_alive"] = False
    data["participants"][index]["rank"] = rank
    data["participants"][index]["death"] = datetime.datetime.now().strftime("Le %d/%m à %H:%M")
    time_alive = datetime.datetime.now().timestamp() - data["start_date"]
    data["participants"][index]["lifetime"] = compute_lifetime(time_alive)

    save_killer_data(data_dir, data)

    victim = {
        "name": name,
        "mission": data["participants"][index]["how_to_kill"],
        "date": data["participants"][index]["death"],
        "rank": rank
    }
    return victim


def assign_kill(data_dir: str, victim: dict, index: int) -> None:
    data = get_killer_data(data_dir)
    data["participants"][index]["kills"].append(victim)
    save_killer_data(data_dir, data)


def count_still_alive(data_dir: str) -> int:
    data = get_killer_data(data_dir)
    participants = data["participants"]
    living = 0
    for player in participants:
        if player["is_alive"]:
            living += 1
    return living


def end_killer(data_dir: str) -> None:
    data = get_killer_data(data_dir)
    data["over"] = True
    save_killer_data(data_dir, data)
    generate_killer_results(data_dir, False)


def change_mission(data_dir: str, player_index :int, new_mission: str) -> None:
    data = get_killer_data(data_dir)
    data["participants"][player_index]["how_to_kill"] = new_mission
    save_killer_data(data_dir, data)


def update_missions(data_dir: str, missions: list) -> None:
    new_missions = []
    for mission in missions:
        if mission["title"]:
            new_missions.append(mission)
    with open(f"{data_dir}/killer/killer_missions.json", "w") as file:
        json.dump(new_missions, file)


def set_killer_ranks(data_dir: str, players: list) -> None:
    data = get_killer_data(data_dir)
    players = data["participants"]
    if not (all(player["rank"] == 0 for player in players)):
        while not any(player["rank"] == 2 for player in players):
            for player in players:
                player["rank"] -= 1
    for player in players:
        if player["rank"] <= 0:
            player["rank"] = 1
    save_killer_data(data_dir, data)


def generate_survie_results(data_dir: str, give_medals: bool) -> None:
    data = get_killer_data(data_dir)
    players = data["participants"]
    teams: dict = dict(Teams=[])
    for team in players:
        if team["rank"] < 4:
            teams["Teams"].append(team)
    for player in teams["Teams"]:
        player["Players"] = player["name"]
        del player["name"]
    if give_medals:
        add_new_results("Killer-Survie", teams, data_dir)


def generate_killer_results(data_dir: str, give_medals: bool) -> None:
    data = get_killer_data(data_dir)
    players = data["participants"]
    set_killer_ranks(data_dir, players)
    generate_survie_results(data_dir, give_medals)
    generate_murders_results(data_dir, give_medals)


def generate_murders_results(data_dir: str, give_medals: bool) -> None:
    data = get_killer_data(data_dir)
    players = data["participants"]
    for player in players:
        player["nr_of_kills"] = len(player["kills"])
    players = sorted(players, key=lambda i: i["nr_of_kills"])  # type: ignore
    players.reverse()
    rank = 1
    players[0]["kills_rank"] = 1
    kills = players[0]["nr_of_kills"]
    new_teams: dict = dict(Teams=[])
    for player in players:
        if player["nr_of_kills"] != kills:
            rank += 1
            if rank == 4:
                break
            kills = player["nr_of_kills"]
        player["kills_rank"] = rank
        new_teams["Teams"].append(player)
    save_killer_data(data_dir, data)
    for player in new_teams["Teams"]:
        player["Players"] = player["name"]
        player["rank"] = player["kills_rank"]
        del player["name"]
    if give_medals:
        add_new_results("Killer-Kills", new_teams, data_dir)


def get_killer_player_info(data_dir: str, name: str) -> dict:
    logging.info(f"Getting player info for {name}")
    data = get_killer_data(data_dir)
    player_index = find_player_index(data_dir, name)
    info = data["participants"][player_index]
    if info["is_alive"]:
        victim_index = find_victim(data_dir, player_index)
        info["target"] = data["participants"][victim_index]["name"]
        info["how_to_kill"] = data["participants"][victim_index]["how_to_kill"]
    return info


def random_kills() -> None:
    """
    For debugging purpose only, do not use during real game
    """
    with open("src/data_serv/killer/killer.json", "r") as file:
        players = json.load(file)["participants"]
    random.shuffle(players)
    while len(players) > 1:
        name = players.pop()["name"]
        kill_player("src/data_serv", name)
        print(f"killed {name}")
