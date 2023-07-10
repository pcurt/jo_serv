import datetime
import json
import logging
import os
import shutil
import time
from typing import Any

from jo_serv.tools.tools import (
    activities_list,
    calculate_rank_clicker,
    players_list,
    send_notif,
)


def event_handler(data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Event handler")
    logger.debug(f"Data dir {data_dir}")
    while True:
        logger.info("Start event_handler loop")
        try:
            events = get_events(data_dir)
            for event in events:
                if event["done"]:
                    continue
                logger.debug(f"Event to check {event}")
                date = date_to_timestamp(event["date"])
                if date_has_passed(date):
                    call_back = get_callback(event["callback"])
                    logger.info(f"Trig event {event}")
                    if "args" in event:
                        args = event["args"]
                        call_back(args, data_dir)
                    else:
                        call_back(data_dir)
                    logger.debug(f"Event {event} done")
                    set_event_done(event["name"], data_dir)
        except Exception as e:
            logger.error(f"Event handler exception {e}")
            send_notif(
                "Pierrick",
                "Event handler",
                f"Failed handling {event['name']}\n logs:\n {e}",
                data_dir,
            )
        time.sleep(60)  # Wait next event


def notif_start_sport(args: dict, data_dir: str) -> None:
    sport = args["sport"]
    to = "all"
    title = sport
    arbitre_str = ""
    body = "Commence!"
    if os.path.exists(f"{data_dir}/teams/{sport}_status.json"):
        with open(f"{data_dir}/teams/{sport}_status.json") as file:
            arbitre = json.load(file)["arbitre"]
            arbitre_str = " ".join(arbitre)
            body += f" Arbitre(s): {arbitre_str}"
    send_notif(to, title, body, data_dir)


def notif_end_sport(args: dict, data_dir: str) -> None:
    sport = args["sport"]
    to = "all"
    title = sport
    body = "Se termine (ou doit se terminer, bougez vous le cul les arbitres)!"
    send_notif(to, title, body, data_dir)


def lock_bets_sport(args: dict, data_dir: str) -> None:
    sport = args["sport"]
    with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
        data = json.load(file)
    if "paris" in data["states"]:
        data["states"].remove("paris")
        data["states"].append("paris_locked")
    with open(f"{data_dir}/teams/{sport}_status.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)


def date_to_timestamp(date: str) -> float:
    return time.mktime(
        datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").timetuple()
    )


def get_events(data_dir: str) -> Any:
    with open(f"{data_dir}/events.json", "r") as file:
        data = json.load(file)
    return data["Events"]


def date_has_passed(date: float) -> bool:
    now = time.time()
    if date < now:
        return True
    return False


def set_event_done(event_name: Any, data_dir: str) -> Any:
    events = get_events(data_dir)
    for event in events:
        if event["name"] == event_name:
            print(f"{event_name} is cleared")
            events.remove(event)
    with open(f"{data_dir}/events.json", "w") as file:
        json.dump(dict(Events=events), file, ensure_ascii=False)


def get_callback(func_name: Any) -> Any:
    return globals()[func_name]


def raz(data_dir: str) -> None:
    raz_results_per_sport(data_dir)
    raz_results_global(data_dir)
    raz_bets_results(data_dir)
    restore_unplayed_matchs(data_dir)
    raz_medals_per_player(data_dir)
    raz_killer_chats(data_dir)
    send_notif("Antoine", "Raz", "Done", data_dir)


def raz_killer_chats(data_dir: str) -> None:
    os.system(f"rm {data_dir}/chat/killer/*.txt")

def raz_results_per_sport(data_dir: str) -> None:
    year = str(datetime.date.today().year)
    for sport in activities_list()[1:-2]:
        if os.path.exists(f"{data_dir}/results/sports/{sport}_summary.json"):
            with open(f"{data_dir}/results/sports/{sport}_summary.json", "r") as file:
                data = json.load(file)
                if year in data:
                    del data[year]
            with open(f"{data_dir}/results/sports/{sport}_summary.json", "w") as file:
                json.dump(data, file)


def raz_results_global(data_dir: str) -> None:
    with open(f"{data_dir}/results/global.json", "r") as file:
        data = json.load(file)
    for player in data:
        player["rank"] = 1
        player["gold"]["number"] = 0
        player["gold"]["sports"] = []
        player["silver"]["number"] = 0
        player["silver"]["sports"] = []
        player["bronze"]["number"] = 0
        player["bronze"]["sports"] = []
    with open(f"{data_dir}/results/global.json", "w") as file:
        json.dump(data, file)


def raz_bets_results(data_dir: str) -> None:
    with open(f"{data_dir}/results/global_bets.json", "r") as file:
        data = json.load(file)
    for player in data:
        player["rank"] = 1
        player["score"] = 0
    with open(f"{data_dir}/results/global_bets.json", "w") as file:
        json.dump(data, file)


def restore_unplayed_matchs(data_dir: str) -> None:
    os.system(f"cp -r {data_dir}/teams/save/*.json {data_dir}/teams/")  # nosec


def raz_medals_per_player(data_dir: str) -> None:
    for player in players_list():
        with open(f"{data_dir}/results/athletes/{player}.json", "r") as file:
            data = json.load(file)
        data["gold_medals"]["number"] = 0
        data["gold_medals"]["sports"] = []
        data["silver_medals"]["number"] = 0
        data["silver_medals"]["sports"] = []
        data["bronze_medals"]["number"] = 0
        data["bronze_medals"]["sports"] = []
        data["points"] = 0
        with open(f"{data_dir}/results/athletes/{player}.json", "w") as file:
            json.dump(data, file)


def test(data_dir: str) -> None:
    send_notif("Antoine", "Just a test", "I'm still alive", data_dir)


def backup_canva(data_dir: str) -> None:
    last_update = os.path.getctime(f"{data_dir}/teams/canva/live_update.json")
    logging.info(f"last up: {last_update}")
    last_backup = os.path.getctime(f"{data_dir}/teams/canva/bak")
    logging.info(f"last backup: {last_backup}")
    now = int(time.time())
    if last_update > last_backup:
        os.system(f"touch {data_dir}/teams/canva/bak/canva{now}.gz")  # nosec
        os.system(  # nosec
            f"tar cfz {data_dir}/teams/canva/bak/canva{now}.gz {data_dir}/teams/canva/*.json"
        )
    with open(f"{data_dir}/events.json", "r") as file:
        data = json.load(file)
    date = datetime.datetime.fromtimestamp(now + 3 * 60).strftime("%Y-%m-%dT%H:%M:%S")
    data["Events"].append(
        dict(name=f"backup: {date}", date=date, callback="backup_canva", done=False)
    )
    with open(f"{data_dir}/events.json", "w") as file:
        json.dump(data, file)
