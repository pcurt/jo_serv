from typing import Any, Dict
from math import ceil
import string
import json
import random


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
            Teams=[dict(Players="", rank=0, score="")] * teams_per_match,
            Selected=3,
        )
        if levels > 0:
            for level in range(1, levels + 1):
                if level != levels:
                    for serie_num in range(2**level):
                        series["Series"].append(
                            dict(
                                Name=f"{level_name[level]}{serie_num+1}",
                                Teams=[dict(Players="", rank=0, score="")] * teams_per_match,
                                Selected=ceil(teams_per_match / 2),
                            )
                        )
                if level == levels:
                    for serie_num in range(int(len(teams)/teams_per_match + 1)):
                        series["Series"].append(
                            dict(
                                Name=f"{level_name[level]}{serie_num+1}",
                                Teams=[],
                                Selected=ceil(teams_per_match / 2),
                            ))
                    for team_number in range(len(teams)):
                        # team fill currently not respecting seeding
                        for serie in series["Series"]:
                            if (
                                f"{level_name[level]}{team_number%int(len(teams)/teams_per_match + 1) + 1}"
                                == serie["Name"]
                            ):
                                serie["Teams"].append(
                                    dict(
                                        Players=teams[team_number]["Players"],
                                        rank=0,
                                        score="",
                                    )
                                )
            series["Series"].append(final)
            return series
        else:
            final = dict(Name="Final", Teams=[], Selected=3, NextSerie=0)
    else:
        final = dict(Name="Final", Teams=[], Selected=3, NextSerie=0)
    for team in teams:
        final["Teams"].append(dict(Players=team["Players"], rank=0, score=""))
    series["Series"].append(final)
    return series


def generate_seeding(teams: list) -> Dict[str, list]:
    print(teams)
    rounds = dict(Rounds=[])
    seeding = dict(Name="Seeding", Teams=[], Selected=len(teams))
    for team in teams:
        seeding["Teams"].append(dict(Players=team["Players"], rank=0, score=""))
    rounds["Rounds"].append(seeding)
    return rounds


def generate_rounds(teams: list, config: Any, states: list, empty: bool, seeding: list=[]) -> Dict[str, list]:
    print(teams)
    teams_per_match = config["Teams per match"]
    number_of_pools = int(len(teams)/teams_per_match) + 1
    number_of_rounds = 1
    pools = 1
    states.append("1er tour")
    rounds = dict(Name="Rounds", Rounds=[])
    rounds["Rounds"].append(dict(Name="1er tour", Teams=number_of_pools*[dict(Teams=4*[""])]))
    while pools < number_of_pools:
        number_of_pools = int(number_of_pools/2)
        number_of_rounds += 1
        states.append(f"{number_of_rounds}e tour")
        if (number_of_pools & (number_of_pools - 1)) != 0:
            number_of_pools = 1 << (number_of_pools.bit_length())
        rounds["Rounds"].append(dict(Name=f"{number_of_rounds}e tour", Teams=number_of_pools*[dict(Teams=4*[""])]))
    if empty:
        return rounds

    

