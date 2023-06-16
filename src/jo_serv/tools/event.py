import glob
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
    generate_pizza_results,
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


def start_happy_hour_clicker(data_dir: str) -> None:
    to = "all"
    title = "Clicker: Happy Hour!"
    save_current_clicker_scores(data_dir)
    with open(f"{data_dir}/teams/Clicker_HH.json", "w") as file:
        json.dump(dict(HH=True), file, ensure_ascii=False)
    send_notif(
        to,
        title,
        "C'est parti! Pour un clic acheté, un clic offert! Profitez en dès maintenant sur \
votre appli préférée. La personne réalisant le meilleur score pendant cette période gagnera \
la possiblité d'envoyer une notif aux personnes de son choix!",
        data_dir,
    )


def notif_end_pizza_vote(data_dir: str) -> None:
    to = "all"
    title = "Vote pizza"
    send_notif(
        to,
        title,
        "Les votes vont bientôt être cloturés pour le concours de Pizza. Il ne vous reste \
qu'un heure pour voter pour votre préférée!",
        data_dir,
    )


def end_happy_hour_clicker(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Clicker_HH.json", "w") as file:
        json.dump(dict(HH=False), file, ensure_ascii=False)
    ranks = compare_clicker_scores(data_dir)
    title = "Clicker: Happy Hour!"
    firsts = ""
    for first in ranks["first"]:
        send_notif(
            first["name"],
            title,
            f"Félicitions! Tu as gagné cette Happy hour avec un score de {first['Clicks']}.\
Encore un click sur cette notification pour gagner ta notif PUSH!",
            data_dir,
        )
        firsts += f"{first['name']} "
    seconds = ""
    for second in ranks["second"]:
        send_notif(
            second["name"],
            title,
            f"Dommage! Cette fois ci ce ne sera que la 2e place pour toi, ton score:\
 {second['Clicks']}",
            data_dir,
        )
        seconds += f"{second['name']} "
    thirds = ""
    for third in ranks["third"]:
        send_notif(
            third["name"],
            title,
            f"3e place! C'est bof, il va falloir s'entrainer pour la prochaine fois, \
ton score: {third['Clicks']}",
            data_dir,
        )
        thirds += f"{third['name']} "
    for noob in ranks["noobs"]:
        send_notif(noob["name"], title, "T'es mauvais!", data_dir)
    message = f"C'est la fin de l'Happy Hour!\n1er:{firsts}score: {first['Clicks']}\n2e:\
 {seconds}score: {second['Clicks']}\n3e: {thirds}score: {third['Clicks']}"
    send_notif("all", title, message, data_dir)


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
            event["done"] = True
            print(f"{event_name} is done")
    with open(f"{data_dir}/events.json", "w") as file:
        json.dump(dict(Events=events), file, ensure_ascii=False)


def get_callback(func_name: Any) -> Any:
    return globals()[func_name]


def set_end_pizza(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Pizza_status.json", "r") as file:
        data = json.load(file)
    data["locked"] = True
    with open(f"{data_dir}/teams/Pizza_status.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)

    generate_pizza_results(data_dir)
    send_notif(
        "all",
        "Vote Pizza terminé",
        "Vous pouvez désormais voir les résultast!",
        data_dir,
    )


def save_current_clicker_scores(data_dir: str) -> None:
    shutil.copy(f"{data_dir}/teams/Clicker.json", f"{data_dir}/teams/Clicker_save.json")


def compare_clicker_scores(data_dir: str) -> dict:
    with open(f"{data_dir}/teams/Clicker.json", "r") as file:
        current_scores = json.load(file)
    with open(f"{data_dir}/teams/Clicker_save.json", "r") as file:
        old_scores = json.load(file)

    clicker = []
    for player_data in current_scores:
        for old_player_data in old_scores:
            if old_player_data["Players"] == player_data["Players"]:
                score = player_data["Clicks"] - old_player_data["Clicks"]
                clicker.append(dict(Players=player_data["Players"], Clicks=score))
    calculate_rank_clicker(clicker, "René Coty")
    results = None
    rank = {}
    rank["first"] = get_nth(1, results)
    rank["second"] = get_nth(2, results)
    rank["third"] = get_nth(3, results)
    rank["noobs"] = get_from_n_to_end(4, results)
    return rank


def get_nth(n: Any, data: Any) -> list:
    new_list: list = []
    for player_data in data:
        if player_data["rank"] == n:
            new_list.append(
                dict(name=player_data["Players"], Clicks=player_data["Clicks"])
            )
    return new_list


def get_from_n_to_end(n: Any, data: Any) -> list:
    new_list = []
    for player_data in data:
        if player_data["rank"] >= n:
            new_list.append(
                dict(name=player_data["Players"], score=player_data["Clicks"])
            )
    return new_list


def raz(data_dir: str) -> None:
    raz_pizza_self_vote(data_dir)
    raz_results_per_sport(data_dir)
    raz_results_global(data_dir)
    raz_bets_results(data_dir)
    restore_unplayed_matchs(data_dir)
    raz_medals_per_player(data_dir)


def raz_pizza_self_vote(data_dir: str) -> None:
    with open(f"{data_dir}/pizza_tas_dhommes.txt", "w") as file:
        file.write("")


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
        with open(f"{data_dir}/results/athletes/{player}.json", "w") as file:
            json.dump(data, file)


def partially_clean_clicker(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Clicker.json", "r") as file:
        data = json.load(file)
        for player in data:
            player["Clicks"] = int(player["Clicks"] / 5)
    with open(f"{data_dir}/teams/Clicker.json", "w") as file:
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
