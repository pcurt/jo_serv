import copy
import datetime
import glob
import json
import logging
import os
import random
import string
from math import ceil
from typing import Any, Dict, Tuple

import requests  # type: ignore


def create_empty_dict(excel_sheet: Any) -> dict:
    athletes: dict = dict()
    for sheet in excel_sheet:
        for column in excel_sheet[sheet]:
            athlete_id = 0
            for _ in excel_sheet[sheet][column]:
                athletes[str(athlete_id)] = dict()
                athlete_id += 1
    return athletes


def store_infos(column: Any, athletes: dict, to_store: Any) -> dict:
    athlete_id = 0
    for data in column:
        athletes[str(athlete_id)][to_store] = data
        athlete_id += 1
    return athletes


def get_sport_config(file_name: str, data_dir: str) -> Any:
    return json.load(open(f"{data_dir}/configs/{file_name}"))


def get_file_name(sport_name: Any, data_dir: str) -> Any:
    lut = json.load(open(f"{data_dir}/configs/LUT.json"))
    return lut[sport_name]


def get_athletes(sport_votes: Any, athletes: Any) -> list:
    athlete_id = 0
    athletes_list = []
    yes_list = ("Participant", "Coureur", "Cuisinier (tout seul ou en equipe)", "Chaud")
    for vote in sport_votes:
        if vote in yes_list:
            athletes_list.append(athletes[str(athlete_id)])
        athlete_id += 1
    random.shuffle(athletes_list)
    return athletes_list


def config_has_team_limit(config: str) -> bool:
    return "Wanted teams" in config


def config_has_player_per_team_limit(config: str) -> bool:
    return "Wanted players per team" in config


def generate_teams(config: Any, athletes: list) -> dict:
    number_of_athletes = len(athletes)
    if config_has_player_per_team_limit(config):
        number_of_teams = int(number_of_athletes / config["Wanted players per team"])
        print(f"Expecting {number_of_teams} teams")
        if number_of_athletes % config["Wanted players per team"]:
            if "Accepted players per team" in config:
                more_teams = (
                    config["Accepted players per team"]
                    < config["Wanted players per team"]
                )
                number_of_teams = (
                    number_of_teams + 1 if more_teams else number_of_teams - 1
                )
    elif config_has_team_limit(config):
        number_of_teams = config["Wanted teams"]
        print(f"Expecting {number_of_teams} teams")
    boobs_number = get_boobs_number(athletes)
    teams: dict = dict()
    for team_number in range(number_of_teams):
        teams[f"team_{team_number}"] = []
    while boobs_number:
        for team in teams:
            for athlete in athletes:
                if athlete["Sexe"] == "F":
                    teams[team].append(athlete["Nom Prénom"])
                    athletes.remove(athlete)
                    boobs_number -= 2
                    break
    for team in teams:
        if len(teams[team]) < len(teams["team_0"]):
            teams[team].append(athletes[0]["Nom Prénom"])
            athletes.remove(athletes[0])
    while athletes:
        for team in teams:
            if athletes:
                teams[team].append(athletes[0]["Nom Prénom"])
                athletes.remove(athletes[0])
    player_per_team = len(teams["team_0"])
    for team in teams:
        if len(teams[team]) < player_per_team:
            teams[team].append("")
    return teams


def get_boobs_number(athletes: Any) -> int:
    boobs_number = 0
    for athlete in athletes:
        if athlete["Sexe"] == "F":
            boobs_number += 2
    return boobs_number


def concatenate_players(excel_sheet: Any, column_name: str) -> str:
    concat_str = ""
    for player in excel_sheet[column_name]:
        if isinstance(player, str):
            concat_str += f"{player}/"
    concat_str = concat_str[:-1]
    return concat_str


def generate_table(teams: list, teams_per_match: int) -> Dict[str, list]:
    nbr_of_teams = len(teams)
    print(f"teams: {nbr_of_teams}")
    nbr_of_matchs = int(nbr_of_teams / teams_per_match) + (
        1 if nbr_of_teams % teams_per_match else 0
    )
    print(f"matchs: {nbr_of_matchs}")
    levels = 0
    matchs = 1
    while matchs < nbr_of_matchs:
        levels += 1
        matchs *= 2
    print(f"levels: {levels}")
    max_nbr_of_matchs = 2**levels
    print(f"max matchs: {max_nbr_of_matchs}")
    start_id = 1
    end_id = max_nbr_of_matchs + 1
    table: dict = dict(matches=[])
    for level in range(levels + 1):
        for unique_id in range(start_id, end_id):
            next_match_id = int((unique_id + 2 - start_id) / 2) + end_id - 1
            match_part = "A" if unique_id % 2 else "B"
            next_match = "" if level == levels else f"{next_match_id}:{match_part}"
            match_dict = dict(
                uniqueId=unique_id,
                team1="",
                team2="",
                score="0:0",
                over=0,
                level=level,
                nextmatch=next_match,
            )
            table["matches"].append(match_dict)
        start_id = end_id
        max_nbr_of_matchs /= 2
        end_id += int(max_nbr_of_matchs)
    table["levels"] = levels + 1
    unique_id = 1
    team_number = 1
    max_nbr_of_matchs = 2**levels
    for team in teams:
        for match_dict in table["matches"]:
            if match_dict["uniqueId"] == unique_id:
                match_dict[f"team{team_number}"] = team["Players"]
        unique_id += 1
        if unique_id > max_nbr_of_matchs:
            team_number = 2
            unique_id = 1

    for match_dict in table["matches"]:
        if match_dict["level"] == 1:
            break
        if not match_dict["team2"]:
            match_dict["over"] = 1
            match_dict["score"] = "23:0"
    return table


def generate_pools(teams: list) -> Dict[str, list]:
    pools: dict = dict(groups=[])
    nbr_of_teams = len(teams)
    print(f"teams: {nbr_of_teams}")
    if not nbr_of_teams % 4:
        nbr_of_pools = int(nbr_of_teams / 4)
    elif nbr_of_teams in (1, 2, 5):
        nbr_of_pools = 1
    else:
        nbr_of_pools = int(nbr_of_teams / 3)
    print(f"pools: {nbr_of_pools}")
    for pool_name in string.ascii_uppercase[:nbr_of_pools]:
        pool: dict = dict(
            name=pool_name, teams=[], over=0, level=0, team_number=0, matches=[]
        )
        pools["groups"].append(pool)
    team_nbr = 0
    for team in teams:
        team_dict = dict(
            name=team["Players"], wins=0, played=0, loses=0, points=0, diff=0
        )
        for pool in pools["groups"]:
            if pool["name"] == string.ascii_uppercase[team_nbr % nbr_of_pools]:
                pool["teams"].append(team_dict)
                pool["team_number"] += 1
                break
        team_nbr += 1
    unique_id = 1
    for pool in pools["groups"]:
        for team_number in range(pool["team_number"] - 1):
            team1 = pool["teams"][team_number]
            for team2 in pool["teams"][team_number + 1 :]:
                match_dict = dict(
                    uniqueId=unique_id,
                    team1=team1["name"],
                    team2=team2["name"],
                    score="0:0",
                    over=0,
                    level=0,
                )
                pool["matches"].append(match_dict)
                unique_id += 1
    for pool in pools["groups"]:
        print(f"poolname: {pool['name']}")
        print(f"teams: {pool['team_number']}")
        for team in pool["teams"]:
            print(team)
        for match in pool["matches"]:
            print(match)
    return pools


def generate_series(teams: list, config: Any) -> Dict[str, list]:
    print(teams)
    series: Dict[str, list] = dict(Series=[])
    if "Teams per match" in config:
        levels = 0
        teams_per_match = config["Teams per match"]
        nb_teams: float = len(teams)
        while nb_teams > teams_per_match:
            nb_teams /= 2
            levels += 1
        level_name = ["Final", "Semi", "Quart", "Huitième", "1er Tour"]
        final: dict = dict(
            Name="Final",
            Teams=[dict(Players="", rank=0)] * teams_per_match,
            Selected=3,
            NextSerie=0,
        )
        if levels > 0:
            series["Series"].append(final)
            for level in range(1, levels + 1):
                for serie_num in range(2**level):
                    series["Series"].append(
                        dict(
                            Name=f"{level_name[level]}{serie_num+1}",
                            Teams=[],
                            Selected=ceil(teams_per_match / 2),
                            NextSerie=0,
                        )
                    )
                if level == levels:
                    for team_number in range(len(teams)):
                        print(team_number)
                        for serie in series["Series"]:
                            print(serie)
                            if (
                                f"{level_name[level]}{team_number%2**levels+1}"
                                == serie["Name"]
                            ):
                                serie["Teams"].append(
                                    dict(
                                        Players=teams[team_number]["Players"],
                                        rank=0,
                                        score="",
                                    )
                                )
                else:
                    for serie in series["Series"]:
                        for _ in range(teams_per_match):
                            serie["Teams"].append(dict(Players="", rank=0, score=""))
            return series
    else:
        final = dict(Name="Final", Teams=[], Selected=3, NextSerie=0)
    for team in teams:
        final["Teams"].append(dict(Players=team["Players"], rank=0, score=""))
    series["Series"].append(final)
    return series


def team_to_next_step(sport: str, match_id: int, data_dir: str) -> None:
    with open(f"{data_dir}/teams/{sport}_playoff.json", "r") as file:
        data = json.load(file)
        matches = data["matches"]
        for match in matches:
            if match["uniqueId"] == match_id:
                results = match["score"].split(":")
                winner = "team1" if int(results[0]) > int(results[1]) else "team2"
                next_match = match["nextmatch"]
                next_match_id = int(next_match.split(":")[0])
                for new_match in matches:
                    if new_match["uniqueId"] == next_match_id:
                        team = "team1" if "A" in next_match else "team2"
                        new_match[team] = match[winner]
                        if not match["over"]:
                            new_match[team] = ""

    with open(f"{data_dir}/teams/{sport}_playoff.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)


def user_is_authorized(username: str, sport: str, data_dir: str) -> bool:
    with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
        data = json.load(file)
        return username in data["arbitre"] or username in (
            "Max",
            "Antoine",
            "Ugo",
            "Pierrick",
        )


def retrieve_score(match_data: dict) -> Tuple[int, int]:
    score = match_data["score"]
    if score.count(":") == 1:
        score_team1, score_team2 = score.split(":")
        return int(score_team1), int(score_team2)
    return 0, 0


def update_playoff_match(
    sport: str, match_id: int, match_data: dict, data_dir: str
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_playoff_match")
    if not match_data["team1"] or not match_data["team2"]:
        return

    score_team1, score_team2 = retrieve_score(match_data)
    with open(f"{data_dir}/teams/{sport}_playoff.json", "r") as file:
        matches_data = json.load(file)
        for match in matches_data["matches"]:
            if match_id == match["uniqueId"]:
                match["score"] = match_data["score"]
                results = match["score"].split(":")
                winner = 1 if score_team1 > score_team2 else 2
                if int(results[0]) == int(results[1]):
                    winner = 0
                match["over"] = match_data["over"]
    with open(f"{data_dir}/teams/{sport}_playoff.json", "w") as file:
        json.dump(matches_data, file, ensure_ascii=False)
    if match_data["level"] != matches_data["levels"] - 1:
        team_to_next_step(sport, match_id, data_dir)
    else:
        teams: dict = dict(Teams=list())
        winner_name = match_data[f"team{winner}"]
        teams["Teams"].append(dict(Players=winner_name, rank=1))
        second = match_data["team1"] if winner == 2 else match_data["team2"]
        teams["Teams"].append(dict(Players=second, rank=2))
        thirds = []
        for match in matches_data["matches"]:
            if match["level"] == matches_data["levels"] - 2:
                third = match["team1"] if match["over"] == 2 else match_data["team2"]
                thirds.append(third)
        for third in thirds:
            teams["Teams"].append(dict(Players=third, rank=3))
        add_new_results(sport, teams, data_dir)
    logger.info("update_playoff_match end")


def update_poules_match(
    sport: str, match_id: int, match_data: dict, data_dir: str
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_poules_match")
    with open(f"{data_dir}/teams/{sport}_poules.json", "r") as file:
        matches_data = json.load(file)
        for poule in matches_data["groups"]:
            if poule["name"] == match_data["poulename"]:
                for match in poule["matches"]:
                    if match_id == match["uniqueId"]:
                        match["score"] = match_data["score"]
                        match["over"] = match_data["over"]
                        poule = compute_points(poule)
    with open(f"{data_dir}/teams/{sport}_poules.json", "w") as file:
        json.dump(matches_data, file, ensure_ascii=False)
    teams: dict = dict(Teams=list())
    with open(f"{data_dir}/teams/{sport}_poules.json", "r") as file:
        matches_data = json.load(file)
        all_poules_over = True
        for poule in matches_data["groups"]:
            if not poule["over"]:
                poule_over = True
                for match in poule["matches"]:
                    if not match["over"]:
                        poule_over = False
                poule["over"] = poule_over
            if not poule_over:
                all_poules_over = False
        if all_poules_over:
            with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
                data = json.load(file)
            if "playoff" in data["states"]:
                for poule in matches_data["groups"]:
                    teams["Teams"].append(dict(Players=get_n_th(poule, 1)["name"]))
                matches_data["groups"].reverse()
                for poule in matches_data["groups"]:
                    teams["Teams"].append(dict(Players=get_n_th(poule, 2)["name"]))
                table = generate_table(teams["Teams"], 2)
                file_name = f"{sport}_playoff.json"
                with open(f"{data_dir}/teams/{file_name}", "w") as file:
                    json.dump(table, file, ensure_ascii=False)
                    data["status"] = "playoff"
                    with open(f"{data_dir}/teams/{sport}_status.json", "w") as file:
                        json.dump(data, file)
            else:
                for poule in matches_data["groups"]:
                    teams["Teams"].append(
                        dict(Players=get_n_th(poule, 1)["name"], rank=1)
                    )
                    teams["Teams"].append(
                        dict(Players=get_n_th(poule, 2)["name"], rank=2)
                    )
                    teams["Teams"].append(
                        dict(Players=get_n_th(poule, 3)["name"], rank=3)
                    )
                add_new_results(sport, teams, data_dir)
        else:
            with open(f"{data_dir}/teams/{sport}_status.json", "r") as file:
                data = json.load(file)
            data["status"] = "poules"
            with open(f"{data_dir}/teams/{sport}_status.json", "w") as file:
                json.dump(data, file)
    logger.info("update_poules_match end")


def get_n_th(poule: dict, n: int) -> Any:
    poule_copy: dict = copy.deepcopy(poule)
    nbr_of_teams: int = len(poule_copy["teams"])
    teams: list = []
    while len(teams) < n:
        highest_pts = 0
        best_team: dict = dict()
        best_diff = 0
        for team in poule_copy["teams"]:
            if len(teams) == nbr_of_teams - 1:
                best_team = poule_copy["teams"][0]
                break
            points = team["points"]
            diff = team["diff"]
            team_name = team["name"]
            if highest_pts < points:
                highest_pts = points
                best_diff = diff
                best_team = team
            elif highest_pts == points:
                if best_diff < diff:
                    highest_pts = points
                    best_diff = diff
                    best_team = team
                elif best_diff == diff:
                    for match in poule_copy["matches"]:
                        if (
                            match["team1"] == best_team["name"]
                            and match["team2"] == team_name
                        ):
                            if match["over"] == 2:
                                best_team == team
                        elif (
                            match["team2"] == best_team["name"]
                            and match["team1"] == team_name
                        ):
                            if match["over"] == 1:
                                best_team == team
        teams.append(best_team)
        poule_copy["teams"].remove(best_team)
    print(teams[-1])
    return teams[-1]


def compute_points(poule: dict) -> dict:
    for team in poule["teams"]:
        team["wins"] = 0
        team["loses"] = 0
        team["diff"] = 0
        team["played"] = 0
        team["points"] = 0
    for match in poule["matches"]:
        if not match["over"]:
            continue
        score_team1, score_team2 = retrieve_score(match)
        if score_team1 or score_team2:
            diff = score_team1 - score_team2
            for team in poule["teams"]:
                if team["name"] == match["team1"]:
                    if diff > 0:
                        team["wins"] += 1
                        team["points"] += 3
                    elif diff < 0:
                        team["loses"] += 1
                    else:
                        team["points"] += 1
                    team["played"] += 1
                    team["diff"] += diff
                if team["name"] == match["team2"]:
                    if diff < 0:
                        team["wins"] += 1
                        team["points"] += 3
                    elif diff > 0:
                        team["loses"] += 1
                    else:
                        team["points"] += 1
                    team["played"] += 1
                    team["diff"] -= diff
    return poule


def update_list(sport: str, data: dict, data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_list")
    with open(f"{data_dir}/teams/{sport}_series.json", "r") as file:
        matches_data = json.load(file)
        for player_data in data:
            level = player_data["level"]
            player_name = player_data["username"]
            serie = matches_data["Series"][level]
            for player in serie["Teams"]:
                if player_name == player["Players"]:
                    player["rank"] = player_data["rank"]
                    if "score" in player_data:
                        player["score"] = player_data["score"]
        if len(matches_data["Series"]) > 1:
            if not all(serie_is_over(serie) for serie in matches_data["Series"][1:]):
                matches_data["Series"][0]["Teams"] = []
                for _ in range(4):
                    matches_data["Series"][0]["Teams"].append(dict(Players="", rank=0))
            elif not serie_is_over(matches_data["Series"][0]):
                matches_data["Series"][0]["Teams"] = []
                for serie in matches_data["Series"][1:]:
                    for player_data in serie:
                        for player in serie["Teams"]:
                            if player["rank"] and player["rank"] <= serie["Selected"]:
                                next = serie["NextSerie"]
                                if not next == -1:
                                    if not any(
                                        team["Players"] == player["Players"]
                                        for team in matches_data["Series"][next][
                                            "Teams"
                                        ]
                                    ):
                                        matches_data["Series"][next]["Teams"].append(
                                            dict(Players=player["Players"], rank=0)
                                        )
                                    print(matches_data["Series"][next]["Teams"])

    with open(f"{data_dir}/teams/{sport}_series.json", "w") as file:
        json.dump(matches_data, file, ensure_ascii=False)
    if "Pizza" in sport:
        return
    teams: dict = dict(Teams=[])
    for team in matches_data["Series"][0]["Teams"]:
        if team["rank"]:
            teams["Teams"].append(team)
    add_new_results(sport, teams, data_dir)
    logger.info("update_list end")


def add_new_results(sport: str, results: Any, data_dir: str) -> None:
    year = str(datetime.date.today().year)
    file_name = f"{sport}_summary.json"
    teams = dict()
    if os.path.exists(f"{data_dir}/results/sports/{file_name}"):
        with open(f"{data_dir}/results/sports/{file_name}", "r") as file:
            teams = json.load(file)

    teams[year] = results
    with open(f"{data_dir}/results/sports/{file_name}", "w") as file:
        json.dump(teams, file, ensure_ascii=False)


def generate_pizza_results(data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("generate_pizza_results")
    players_score: list = []
    for player in players_list():
        players_score.append(dict(Players=player, score=0))
    for judge in players_list():
        with open(f"{data_dir}/teams/Pizza/{judge}_series.json", "r") as pizz_file:
            for team in json.load(pizz_file)["Series"][0]["Teams"]:
                if team["rank"] == 1:
                    for someone in players_score:
                        if someone["Players"] in team["Players"]:
                            someone["score"] += 1
    players_score = sorted(players_score, key=lambda i: i["score"])  # type: ignore
    players_score.reverse()
    max_score = players_score[0]["score"]
    rank = 1
    for player in players_score:
        if player["score"] == max_score:
            player["rank"] = rank
        else:
            max_score = player["score"]
            rank += 1
            if rank == 4:
                break
            player["rank"] = rank
    with open(f"{data_dir}/results/sports/Pizza_summary.json", "w") as file:
        json.dump(dict(Teams=players_score), file, ensure_ascii=False)
    logger.info("generate_pizza_results end")


def serie_is_over(serie: dict) -> bool:
    selected = serie["Selected"]
    if selected:
        for rank in range(selected):
            if all(team["rank"] != rank for team in serie["Teams"]):
                return False
            else:
                print(f"Serie has n°{rank}")
        return True
    return False


def log(sport: str, username: str, data: Any, data_dir: str) -> None:
    with open(f"{data_dir}/logs/{sport}.log", "a") as file:
        date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        file.write(f"{date}: {username}:\n {data}\n")


# def fix_json(data_dir):
#    for filename in os.listdir("/home/JO/JO_server/teams"):
#        if ".json" in filename:
#            path = data_dir + "/home/JO/JO_server/teams"
#            file_handler = open(os.path.join(path, filename), "a")
#            file_handler.write("\n\n\n\n")
#            file_handler.close()


def players_list() -> list:
    return [
        "Jo",
        "Antoine",
        "Thomas",
        "Reminem",
        "Shmav",
        "LaGuille",
        "Ugo",
        "Chloé",
        "Brice",
        "Max",
        "Bryan",
        "Keke",
        "Alissone",
        "Alice",
        "Mathieu",
        "Pierrick",
        "Mimo",
        "Gui",
        "Chachav",
        "Jess",
        "Mams",
        "Jason",
        "Gazou",
        "Babouche",
        "Clement",
        "Bifteck",
    ]


def activities_list(include_date: bool = False) -> Any:
    if include_date:
        return {
            "Soirée d'ouverture!": ["2022-07-13T20:00:00", "2022-07-14T09:30:00"],
            "Trail": ["2022-07-14T09:30:00", "2022-07-14T11:00:00"],
            "Dodgeball": ["2022-07-14T11:00:00", "2022-07-14T13:00:00"],
            "PingPong": ["2022-07-14T11:00:00", "2022-07-14T13:00:00"],
            "Pizza": ["2022-07-14T12:00:00", "2022-07-14T15:00:00"],
            "Volley": ["2022-07-14T14:00:00", "2022-07-14T17:00:00"],
            "SpikeBall": ["2022-07-14T14:00:00", "2022-07-14T17:00:00"],
            "Krossfit": ["2022-07-14T17:00:00", "2022-07-14T18:00:00"],
            "Corde": ["2022-07-14T18:00:00", "2022-07-14T19:00:00"],
            "Orientation": ["2022-07-14T19:00:00", "2022-07-14T20:00:00"],
            "Beerpong": ["2022-07-15T10:00:00", "2022-07-15T14:00:00"],
            "Waterpolo": ["2022-07-15T14:00:00", "2022-07-15T15:00:00"],
            "Larmina": ["2022-07-15T14:00:00", "2022-07-15T15:00:00"],
            "Blindtest": ["2022-07-15T14:00:00", "2022-07-15T15:00:00"],
            "Tong": ["2022-07-15T15:00:00", "2022-07-14T17:00:00"],
            "Babyfoot": ["2022-07-15T15:00:00", "2022-07-14T17:00:00"],
            "Flechette": ["2022-07-15T15:00:00", "2022-07-14T17:00:00"],
            "Slackline": ["2022-07-15T15:00:00", "2022-07-14T17:00:00"],
            "Ventriglisse": ["2022-07-15T17:00:00", "2022-07-15T19:00:00"],
            "100mRicard": ["2022-07-15T21:00:00", "2022-07-16T04:00:00"],
            "Petanque": ["2022-07-16T11:00:00", "2022-07-16T13:00:00"],
            "Rangement": ["2022-07-16T14:00:00", "2022-07-16T15:30:00"],
            "Remise des prix": ["2022-07-16T15:30:00", "2022-07-16T17:30:00"],
        }
    return [
        "Soirée d'ouverture!",
        "Trail",
        "Dodgeball",
        "PingPong",
        "Pizza",
        "Volley",
        "SpikeBall",
        "Krossfit",
        "Corde",
        "Orientation",
        "Beerpong",
        "Waterpolo",
        "Larmina",
        "Blindtest",
        "Tong",
        "Babyfoot",
        "Flechette",
        "Slackline",
        "Ventriglisse",
        "100mRicard",
        "Petanque",
        "Rangement",
        "Remise des prix",
    ]


def sort_list(old_list: list) -> list:
    new_list: list = []
    for activity in activities_list():
        if activity in old_list:
            new_list.append(activity)
    return new_list


def get_results(athlete: Any, data_dir: str) -> dict:
    logger = logging.getLogger(__name__)
    logger.info("get_results")
    results: dict = dict(nr1=[], nr2=[], nr3=[])
    for filename in os.listdir(f"{data_dir}/results/sports/"):
        logger.info(f"{filename}")
        if "_summary.json" in filename:
            sport = filename.replace("_summary.json", "")
            with open(f"{data_dir}/results/sports/{filename}", "r") as file:
                current_year = str(datetime.date.today().year)
                sport_results = json.load(file)
                if current_year in sport_results:
                    for team in sport_results[current_year]["Teams"]:
                        logger.info(team)
                        if athlete in team["Players"]:
                            rank = team["rank"]
                            results[f"nr{rank}"].append(sport)
    return results


def get_bet_score(player: Any, data_dir: str) -> dict:
    logger = logging.getLogger(__name__)
    logger.info("get_bet_score")
    score = 0
    for filename in os.listdir(f"{data_dir}/results/sports/"):
        logger.info(f"{filename}")
        if "_summary.json" in filename:
            sport = filename.replace("_summary.json", "")
            logger.info(f"Bet result for {sport}")
            with open(f"{data_dir}/results/sports/{filename}", "r") as file:
                current_year = str(datetime.date.today().year)
                sport_results = json.load(file)
                logger.debug(f"All sport result : {sport_results}")
                if current_year in sport_results:
                    for team in sport_results[current_year]["Teams"]:
                        logger.info(f"Team is {team}")

                        if team["rank"] == 1 or team["rank"] == 2 or team["rank"] == 3:
                            logger.debug(
                                f"Reading file  : {data_dir}/bets/{sport}.json"
                            )
                            with open(f"{data_dir}/bets/{sport}.json") as f:
                                data = json.load(f).get("Teams")
                                for bet_team in data:
                                    if bet_team["Players"] == team["Players"]:
                                        if player in bet_team["Votes"]:
                                            if team["rank"] == 1:
                                                points = 9
                                            elif team["rank"] == 2:
                                                points = 5
                                            else:
                                                points = 3
                                            score = score + points
                                            logger.info(
                                                f"{player} has voted for wining team in {sport}"
                                            )
    bet_result = dict(player=player, score=score)
    return bet_result


def update_results(athlete: Any, data_dir: str) -> dict:
    results: dict = get_results(athlete, data_dir)
    gold_medals = len(results["nr1"])
    silver_medals = len(results["nr2"])
    bronze_medals = len(results["nr3"])
    points = bronze_medals + 20 * silver_medals + 400 * gold_medals
    final_results: dict = dict(
        gold_medals=dict(number=gold_medals, sports=results["nr1"]),
        silver_medals=dict(number=silver_medals, sports=results["nr2"]),
        bronze_medals=dict(number=bronze_medals, sports=results["nr3"]),
        points=points,
    )
    with open(f"{data_dir}/results/athletes/{athlete}.json", "w") as file:
        json.dump(final_results, file)
    return final_results


def update_global_results(data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_global_results")
    results = []
    for athlete in players_list():
        logger.info(f"Update player {athlete}")
        result = update_results(athlete, data_dir)
        result["name"] = athlete
        results.append(result)
        print(result)
    results = sorted(results, key=lambda i: i["points"])  # type: ignore
    results.reverse()
    rank = 0
    score = 1000000  # vous voyez ce que ça fait déjà 1 million Larmina ?
    inc = 1
    final_results = []
    for result in results:
        if result["points"] < score:
            score = result["points"]
            rank += inc
            inc = 1
        else:
            inc += 1
        res = dict(
            rank=rank,
            name=result["name"],
            gold=result["gold_medals"],
            silver=result["silver_medals"],
            bronze=result["bronze_medals"],
        )
        final_results.append(res)

    with open(f"{data_dir}/results/global.json", "w") as file:
        json.dump(final_results, file)
    logger.info("update_global_results ended")


def update_global_bets_results(data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_global_bets_results")
    results = []
    for athlete in players_list():
        logger.info(f"Update player {athlete}")
        result = get_bet_score(athlete, data_dir)
        results.append(result)
        logger.info(f"Bet result is {result}")

    results = sorted(results, key=lambda i: i["score"], reverse=True)  # type: ignore

    final_results = []
    global_rank = 0
    prev_score = 0
    prev_rank = 0
    for result in results:
        global_rank = global_rank + 1
        if result["score"] != prev_score:
            rank = global_rank
        else:
            rank = prev_rank
        prev_rank = rank
        prev_score = result["score"]
        res = dict(rank=rank, player=result["player"], score=result["score"])
        final_results.append(res)

    with open(f"{data_dir}/results/global_bets.json", "w") as file:
        json.dump(final_results, file, ensure_ascii=False, indent=4)
    logger.info("update_global_bets_results ended")


def generate_event_list(name: str, data_dir: str) -> None:
    arbitre_list: list = []
    playing_list: list = []
    parse_json(name, ".json", playing_list, data_dir)
    arbitre_list = sort_list(arbitre_list)
    playing_list = sort_list(playing_list)
    print(arbitre_list)
    print(playing_list)
    with open(f"{data_dir}/athletes/{name}.json", "w") as athlete_file:
        json.dump(dict(arbitre=arbitre_list, activities=playing_list), athlete_file)


def parse_json(
    name_searched: str,
    suffix: str,
    list_to_append: list,
    data_dir: str,
    exclude: str = None,
) -> None:
    for filename in os.listdir(f"{data_dir}/teams/"):
        if suffix in filename:
            if exclude is None or filename not in exclude:
                with open(f"{data_dir}/teams/{filename}", "r") as file:
                    if name_searched in file.read():
                        list_to_append.append(filename.split(suffix)[0])


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


def send_notif(to: str, title: str, body: str, data_dir: str) -> None:
    to = to.replace(" ", "")
    with open(f"{data_dir}/tokens.txt", "r") as tokens_file:
        tokens = tokens_file.readlines()
    tokens_list = tokens
    if to not in ("all", "All"):
        tokens_list = []
        for token in tokens:
            for person in to.split(","):
                if person in token:
                    tokens_list.append(token)
    for token in tokens_list:
        if "ExponentPushToken" in token:
            data = {"to": token.split(":")[0], "title": title, "body": body}
            requests.post("https://exp.host/--/api/v2/push/send", data=data)


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


def lock(sportname: str, data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("lock sport")
    with open(f"{data_dir}/teams/{sportname}_status.json", "r") as file:
        data = json.load(file)
        data["locked"] = True

    with open(f"{data_dir}/teams/{sportname}_status.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)


def unlock(sportname: str, data_dir: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("unlock sport")
    with open(f"{data_dir}/teams/{sportname}_status.json", "r") as file:
        data = json.load(file)
        data["locked"] = False

    with open(f"{data_dir}/teams/{sportname}_status.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)


def end_sport(sportname: str, data_dir: str) -> None:
    with open(f"{data_dir}/teams/{sportname}_status.json", "a") as file:
        status = json.load(file)
        status["status"] = "results"
        json.dump(status, file)
    send_notif("all", sportname, "Vous pouvez désormais voir les résultast!", data_dir)


def add_events_to_handler(data_dir: str) -> None:
    with open(f"{data_dir}/events.json", "r") as file:
        data = json.load(file)
    events = data["Events"]
    activities = activities_list(True)
    for activity in activities:
        new_event_start = {
            "name": f"Start {activity}",
            "date": activities[activity][0],
            "callback": "notif_start_sport",
            "args": {"sport": activity},
            "done": False,
        }
        new_event_end = {
            "name": f"End {activity}",
            "date": activities[activity][1],
            "callback": "notif_end_sport",
            "args": {"sport": activity},
            "done": False,
        }
        events.append(new_event_start)
        events.append(new_event_end)
    with open(f"{data_dir}/events.json", "w") as file:
        json.dump(dict(Events=events), file, ensure_ascii=False)
