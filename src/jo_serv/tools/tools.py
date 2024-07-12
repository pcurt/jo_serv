import datetime
import glob
import hashlib
import json
import logging
import os
import random
import re
import shutil
import string
from typing import Any
import requests  # type: ignore

CANVA_SIZE = 50
palette_colors = [
    "white",
    "purple",
    "darkblue",
    "blue",
    "lightblue",
    "green",
    "lightgreen",
    "yellow",
    "brown",
    "orange",
    "red",
    "pink",
    "lightgrey",
    "grey",
    "black",
]


def log(sport: str, username: str, data: Any, data_dir: str) -> None:
    with open(f"{data_dir}/logs/{sport}.log", "a") as file:
        date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        file.write(f"{date}: {username}:\n {data}\n")


def user_is_authorized(username: str, sport: str, data_dir: str) -> bool:
    with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
        data = json.load(file)
        return username in data["arbitre"] or username in (
            "Max",
            "Antoine",
            "Ugo",
            "Pierrick",
        )


def players_list(data_dir: str) -> list:
    with open(f"{data_dir}/athletes/All.json", "r") as file:
        data = json.load(file)
    to_return = []
    for player in data:
        to_return.append(player["Player"])
    return to_return


def generate_account(data_dir: str, user: str) -> None:
    with open(f"{data_dir}/login.json", "r") as file:
        users = json.load(file)["users"]
    if not any(user == known_user["username"] for known_user in users):
        users.append(
            dict(
                username=user,
                password="".join(
                    random.choices(string.ascii_letters + string.digits, k=4)
                ),
            )
        )
        print(f"{user} added")
    else:
        print(f"{user} already has an account")
    with open(f"{data_dir}/login.json", "w") as file:
        json.dump(dict(users=users), file)


def activities_list(data_dir: str, include_date: bool = False) -> Any:
    with open(f"{data_dir}/planning.json", "r") as file:
        data = json.load(file)
    if include_date:
        return data
    activities = []
    for name in data:
        activities.append(name)
    return activities


def sports_list(data_dir: str) -> list:
    with open(f"{data_dir}/planning.json", "r") as file:
        data = json.load(file)
    activities = []
    for name in data:
        if data[name][2] == "SportDetails":
            activities.append(name)
    return activities


def sort_list(data_dir: str, old_list: list) -> list:
    new_list: list = []
    for activity in activities_list(data_dir):
        if activity in old_list:
            new_list.append(activity)
    return new_list


def generate_event_list(name: str, data_dir: str) -> None:
    arbitre_list: list = []
    playing_list: list = []
    parse_json(name, "_series.json", playing_list, f"{data_dir}/teams")
    parse_json(name, "_playoff.json", playing_list, f"{data_dir}/teams")
    parse_json(name, "_poules.json", playing_list, f"{data_dir}/teams")
    get_arbitre_list(name, arbitre_list, data_dir)
    arbitre_list = sort_list(data_dir, arbitre_list)
    playing_list = sort_list(data_dir, playing_list)
    print(arbitre_list)
    print(playing_list)
    with open(f"{data_dir}/athletes/{name}.json", "w") as athlete_file:
        json.dump(dict(arbitre=arbitre_list, activities=playing_list), athlete_file)


def get_arbitre_list(name: str, arbitre_list: list, data_dir: str) -> None:
    for filename in os.listdir(f"{data_dir}/teams/"):
        if "_status.json" in filename:
            with open(f"{data_dir}/teams/{filename}", "r") as file:
                data = json.load(file)
            if "arbitre" in data:
                for arbitre in data["arbitre"]:
                    if arbitre == name:
                        arbitre_list.append(filename.split("_status.json")[0])


def parse_json(
    name_searched: str,
    suffix: str,
    list_to_append: list,
    directory: str,
    exclude: str = None,
) -> None:
    for filename in os.listdir(directory):
        if suffix in filename:
            if exclude is None or exclude not in filename:
                with open(f"{directory}/{filename}", "r") as file:
                    if re.findall(f"\\b{name_searched}\\b", file.read()):
                        list_to_append.append(filename.split(suffix)[0])


def send_notif(to: str, title: str, body: str, data_dir: str) -> None:
    to = to.replace(" ", "")
    with open(f"{data_dir}/tokens.txt", "r") as tokens_file:
        tokens = tokens_file.readlines()
    tokens_list = tokens
    if to not in ("all", "All"):
        tokens_list = []
        for token in tokens:
            if ":" in token:
                for person in to.split(","):
                    if person == token.rsplit(":", 1)[1].replace("\n", ""):
                        tokens_list.append(token)
    for token in tokens_list:
        if "ExponentPushToken" in token:
            data = {"to": token.split(":")[0], "title": title, "body": body}
            requests.post("https://exp.host/--/api/v2/push/send", data=data)
            logging.info(data)


def get_all_event_list(data_dir: str) -> list:
    logger = logging.getLogger(__name__)
    logger.info("get_all_event_list")
    all_event = []
    for file in glob.glob(f"{data_dir}/teams/*.json"):
        if "_status" not in file and "_poules" not in file:
            if "_series" not in file and "_playoff" not in file:
                if "_ts" not in file and "_save" not in file:
                    logger.debug(f"Files is : {file}")
                    event = os.path.basename(file).split(".")[0]
                    logger.info(f"Found Event : {event}")
                    all_event.append(event)
    return all_event


def create_empty_bet_files(data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("create_empty_bet_files")
    all_event = get_all_event_list(data_dir)
    for event in all_event:
        # Opening JSON file
        f = open(f"{data_dir}/teams/{event}.json")
        # returns JSON object as  # a dictionary
        all_bets: list = []
        logger.info(f"Reading file  : {data_dir}/teams/{event}.json")
        try:
            data = json.load(f)
            teams = data.get("Teams")
            logger.debug(f"Teams : {teams}")
            for team in teams:
                players = team["Players"]
                logger.debug(f"Players : {players}")
                bet: dict = dict()
                # Create empty entry
                bet["Players"] = players
                bet["Votes"] = []
                bet["Rank"] = 1
                bet["TotalVotes"] = 0
                logger.info(f"Bet for event {event}: {bet}")
                all_bets.append(bet)
            logger.info(f"All bets : {all_bets}")
            with open(f"{data_dir}/bets/{event}.json", "w") as file:
                json.dump(dict(Teams=all_bets), file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error reading file : {data_dir}/teams/{event}.json")
            logger.error(f"Error {e}")


def update_bet_file(data_dir: str, sport: str, username: str, bets: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_bet_file")
    # TODO Check if event is locked or not
    logger.info(f"Reading file  : {data_dir}/bets/{sport}.json")
    with open(f"{data_dir}/bets/{sport}.json") as f:

        data = json.load(f).get("Teams")
        logger.info(f"Raw data is{data}")
        for idx, team in enumerate(data):
            logger.info(f"Iteartion {idx}, {team}")
            logger.info(data[idx]["Votes"])
            logger.info(team["Players"])
            logger.info(bets)
            logger.info(username)
            # Delete other enries for this user
            try:
                data[idx]["Votes"].remove(username)
            except ValueError:
                pass
            if team["Players"] == bets:
                logger.info(f"Add bet for {username, bets}")
                data[idx]["Votes"].append(username)
            # Update totalvotes
            data[idx]["TotalVotes"] = len(data[idx]["Votes"])
    with open(f"{data_dir}/bets/{sport}.json", "w") as f:
        json.dump(dict(Teams=data), f, ensure_ascii=False)


def adapt_bet_file(data_dir: str, sport: str) -> None:
    with open(f"{data_dir}/bets/{sport}.json", "r") as bets_file:
        bets = json.load(bets_file).get("Teams")
    with open(f"{data_dir}/teams/{sport}.json", "r") as teams_file:
        teams = json.load(teams_file).get("Teams")
    for bet_team in bets:
        if not any(bet_team["Players"] == team["Players"] for team in teams):
            bets.remove(bet_team)
    for team in teams:
        if not any(team["Players"] == bet_team["Players"] for bet_team in bets):
            bets.append(dict(Players=team["Players"], Votes=[], TotalVotes=0))
    with open(f"{data_dir}/bets/{sport}.json", "w") as bets_file:
        json.dump(dict(Teams=bets), bets_file)
    with open(f"{data_dir}/teams/{sport}.json", "w") as teams_file:
        json.dump(dict(Teams=teams), teams_file)


def add_events_to_handler(data_dir: str) -> None:
    with open(f"{data_dir}/events.json", "r") as file:
        data = json.load(file)
    events = data["Events"]
    activities = activities_list(data_dir, True)
    for activity in activities:
        new_event_start = {
            "name": f"Start {activity}",
            "date": activities[activity][0].split("+")[0],
            "callback": "notif_start_sport",
            "args": {"sport": activity},
            "done": False,
        }
        events.append(new_event_start)
        new_event_end = {
            "name": f"End {activity}",
            "date": activities[activity][1].split("+")[0],
            "callback": "notif_end_sport",
            "args": {"sport": activity},
            "done": False,
        }
        events.append(new_event_end)
        if (activities[activity][2] == "SportDetails"):
            new_event_lock = {
                "name": f"Lock bets {activity}",
                "date": activities[activity][0].split("+")[0],
                "callback": "lock_bets_sport",
                "args": {"sport": activity},
                "done": False,
            }
            events.append(new_event_lock)
    with open(f"{data_dir}/events.json", "w") as file:
        json.dump(dict(Events=events), file, ensure_ascii=False)


def increase_canva_size(data_dir: str, tile_x: int, tile_y: int) -> None:
    logger = logging.getLogger(__name__)
    logger.info("increase_canva_size")
    for tocheck in [tile_x, tile_y]:
        if tocheck < 0:
            # if tocheck % CANVA_SIZE != 0:
            logger.error(f"{tocheck.__str__()} number must be  positive")
            return

    # todo : change global size of canva in esrver.py +
    # may be change appli so it sends its actual size
    # size_mutex.acquire()
    # try:
    size_json = json.load(open(f"{data_dir}/teams/canva/sizecanva.json", "r"))
    # finally::
    # size_mutex.release()
    actual_lines_nb = int(size_json.get("lines"))
    actual_cols_nb = int(size_json.get("cols"))
    number_canva = int(size_json.get("numbercanva"))
    actual_canva_per_line = int(actual_cols_nb / CANVA_SIZE)
    new_canva_per_line = actual_canva_per_line + tile_x
    actual_canva_per_col = int(actual_lines_nb / CANVA_SIZE)
    new_number_canva = number_canva + actual_canva_per_col * tile_x
    new_number_canva += new_canva_per_line * tile_y
    # first we need to rename existing canvas
    list_missing = [x for x in range(actual_canva_per_line, new_number_canva)]
    empty_canva: list = [dict(color="white", name="Whisky")] * CANVA_SIZE * CANVA_SIZE
    file_to_rename = []
    if tile_x != 0:
        offset = 0
        for i in range(actual_canva_per_line, number_canva):
            if i % actual_canva_per_line == 0:
                offset += tile_x
            list_missing.remove(i + offset)
            # canva_array_mutex[i].acquire()
            # try:
            file_to_rename.append(f"{data_dir}/teams/canva/canva{i+offset}_tmp.json")
            shutil.copyfile(
                f"{data_dir}/teams/canva/canva{i}.json",
                f"{data_dir}/teams/canva/canva{i+offset}_tmp.json",
            )
        for i in list_missing:
            with open(f"{data_dir}/teams/canva/canva{i}.json", "w") as file:
                json.dump(empty_canva, file)
        for filename in file_to_rename:
            shutil.move(filename, filename.replace("_tmp.json", ".json"))
            # finally:
            #     canva_array_mutex[i].release()
    if tile_y != 0:  # way easier, we just create at the end!
        for i in range(number_canva, new_number_canva):
            with open(f"{data_dir}/teams/canva/canva{i}.json", "w") as file:
                json.dump(empty_canva, file)
    for filename in os.listdir(f"{data_dir}/teams/canva"):
        if ".json" in filename and "canva" in filename:
            if not os.path.exists(
                f"{data_dir}/teams/canva/" + filename.replace(".json", ".sha256")
            ):
                with open(f"{data_dir}/teams/canva/" + filename, "r") as file:
                    data = file.read()
                m = hashlib.sha256()
                m.update(str.encode(data))
                with open(
                    f"{data_dir}/teams/canva/" + filename.replace(".json", ".sha256"),
                    "w",
                ) as file:
                    file.write(m.hexdigest())
    size_json["lines"] = int(size_json["lines"]) + tile_y * CANVA_SIZE
    size_json["cols"] = int(size_json["cols"]) + tile_x * CANVA_SIZE
    size_json["numbercanva"] = new_number_canva
    json.dump(size_json, open(f"{data_dir}/teams/canva/sizecanva.json", "w"))


def get_non_registered(sport: str, data_dir: str) -> list:
    with open(f"{data_dir}/teams/{sport}.json", "r") as file:
        data = json.load(file)
        non_registered = []
        for player in players_list(data_dir):
            if not any(player in team["Players"] for team in data["Teams"]):
                non_registered.append(player)
    return non_registered


def generate_can_be_added_list(sport: str, data_dir: str) -> None:
    non_registered = get_non_registered(sport, data_dir)
    with open(f"{data_dir}/teams/{sport}.json", "r") as file:
        data = json.load(file)
    data["Others"] = []
    for player in non_registered:
        data["Others"].append(dict(Players=player))
    with open(f"{data_dir}/teams/{sport}.json", "w") as file:
        json.dump(data, file)


def toggle_lock_bets(sport: str, data_dir: str) -> None:
    with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
        data = json.load(file)
    if "paris" in data["states"]:
        data["states"].remove("paris")
        data["states"].append("paris_locked")
    else:
        data["states"].remove("paris_locked")
        data["states"].append("paris")
    with open(f"{data_dir}/teams/{sport}_status.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)


def get_palmares(data_dir: str, name: str) -> dict:
    sport_list: list[str] = []
    palmares = dict()
    parse_json(name, "_summary.json", sport_list, f"{data_dir}/results/sports", "votes")
    for sport in sport_list:
        palmares[sport] = dict()
        with open(f"{data_dir}/results/sports/{sport}_summary.json", "r") as file:
            results = json.load(file)
        for year in results:
            for team in results[year]["Teams"]:
                if re.findall(f"\\b{name}\\b", team["Players"]):
                    palmares[sport][year] = team["rank"]
    return palmares


def populate_rangement(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Rangement.json", "r") as file:
        data = json.load(file)
    players = []
    for player in players_list(data_dir):
        players.append(dict(name=player, busy=False, score=0))
    data["Players"] = players
    with open(f"{data_dir}/teams/Rangement.json", "w") as file:
        json.dump(data, file)


def clear_rangement(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Rangement.json", "r") as file:
        data = json.load(file)
    for task in data["tasks"]:
        task["state"] = 0
        task["participants"] = []
    with open(f"{data_dir}/teams/Rangement.json", "w") as file:
        json.dump(data, file)
    populate_rangement(data_dir)
