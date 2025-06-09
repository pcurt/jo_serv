import re
import copy
import json
import logging
import datetime
import os
from typing import Any, Tuple
from jo_serv.tools.excel_mgmt import generate_table, get_sport_config, get_file_name
from jo_serv.tools.tools import send_notif, players_list


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


def retrieve_score(match_data: dict) -> Tuple[int, int]:
    score = match_data["score"]
    if score.count(":") == 1:
        score_team1, score_team2 = score.split(":")
        return int(score_team1), int(score_team2)
    return 0, 0


def update_vote(data_dir: str, username: str, vote: str, sportname: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_vote")
    # TODO Check if event is locked or not
    logger.info(f"Reading file  : {data_dir}/teams/{sportname}_votes.json")
    with open(f"{data_dir}/teams/{sportname}_votes.json") as f:
        matches_data = json.load(f)
    data = matches_data["Teams"]
    logger.info(f"Raw data is{data}")
    for player in data:
        if username in player["votes"]:
            player["votes"].remove(username)
        if vote == player["Players"]:
            player["votes"].append(username)
    print(f"matches_data {matches_data}")
    with open(f"{data_dir}/teams/{sportname}_votes.json", "w") as f:
        json.dump(matches_data, f, ensure_ascii=False, indent=4)


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
                logger.info(match)
                third = match["team1"] if match["over"] == 2 else match["team2"]
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
                if len(matches_data["groups"]) == 1:
                    poule = matches_data["groups"][0]
                    teams["Teams"].append(dict(Players=get_n_th(poule, 1)["name"]))
                    teams["Teams"].append(dict(Players=get_n_th(poule, 2)["name"]))
                elif len(matches_data["groups"]) == 2:
                    for poule in matches_data["groups"]:
                        teams["Teams"].append(dict(Players=get_n_th(poule, 1)["name"]))
                    matches_data["groups"].reverse()
                    for poule in matches_data["groups"]:
                        teams["Teams"].append(dict(Players=get_n_th(poule, 2)["name"]))
                elif len(matches_data["groups"]) == 3:
                    temp_teams: dict = dict(teams=[])
                    for poule in matches_data["groups"]:
                        temp_teams["teams"].append(get_n_th(poule, 2))
                        logger.info(temp_teams)
                    selected = get_n_th(temp_teams, 1)["name"]
                    teams["Teams"].append(dict(Players=selected))
                    logger.info(selected)
                    logger.info(matches_data)
                    if any(
                        selected == poule["name"] for poule in matches_data["groups"]
                    ):
                        matches_data["groups"].reverse()
                    for poule in matches_data["groups"]:
                        teams["Teams"].append(dict(Players=get_n_th(poule, 1)["name"]))
                elif len(matches_data["groups"]) == 4:
                    for poule in matches_data["groups"]:
                        teams["Teams"].append(dict(Players=get_n_th(poule, 1)["name"]))
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


def update_list(sport: str, data: dict, data_dir: str, serie_to_update: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("update_list")
    sport_config = get_sport_config(f"{sport}.json", data_dir)
    with open(f"{data_dir}/teams/{sport}_series.json", "r") as file:
        matches_data = json.load(file)
        # Find serie
        server_serie = None
        for serie in matches_data["Series"]:
            if serie["Name"] == serie_to_update:
                server_serie = serie
        if server_serie == None:
            raise Exception(f"Coulnd't find serie: {serie_to_update}")
        if server_serie["InProgress"] == False:
            raise Exception(f"Serie: {serie_to_update} can't be updated yet")
        # Find players in this serie
        players = []
        all_scores_entered = True
        for player_data in data:
            serie_competing = player_data["series_name"]
            if serie_competing != serie_to_update:
                continue
            players.append(player_data)
            if "Ranks on score" in sport_config:
                all_scores_entered = all_scores_entered if player_data["score"] != "" else False
        # Update their scores/ranks
        for server_player in server_serie["Teams"]:
            for player_data in players:
                if server_player["Players"] == player_data["username"]:
                    server_player["rank"] = player_data["rank"]
                    server_player["score"] = player_data["score"]
        # Check if we can set the serie as Over
        if "Ranks on score" in sport_config and all_scores_entered:
            server_serie["Teams"] = sorted(server_serie["Teams"], key=lambda i: int(i["score"]))
            if sport_config["Series rank"] == "highest":
                server_serie["Teams"].reverse()
            max_score = server_serie["Teams"][0]["score"]
            rank = 1
            server_serie["Teams"][0]["rank"] = rank
            next_rank = 1
            for player in server_serie["Teams"][1:]:
                if player["score"] == max_score:
                    player["rank"] = rank
                    next_rank += 1
                else:
                    max_score = player["score"]
                    rank += next_rank
                    next_rank = 1
                    player["rank"] = rank
            server_serie["Over"] = True
        else:
            medals = 0
            for player in server_serie["Teams"]:
                if player["rank"] < 4: 
                    medals += 1
            server_serie["Over"] = medals > 2
        level = server_serie["Level"]
        # If not final check if all series are over for this round, if so start next one
        if level != 0:
            if all(serie["Over"] or serie["Level"] != level for serie in matches_data["Series"]):
                teams_per_match = sport_config["Teams per match"]
                required_players = teams_per_match * 2**(level - 1)
                number_of_series = 0
                all_players = []
                for serie in matches_data["Series"]:
                    if serie["Level"] == level:
                        number_of_series += 1
                        for player in serie["Teams"]:
                            all_players.append(player)
                all_players = sorted(all_players, key=lambda i: int(i["score"]))
                all_players.reverse()
                all_players = sorted(all_players, key=lambda i: int(i["rank"]))[:required_players]
                logger.info(all_players)
                for i in range(teams_per_match):
                    for serie in matches_data["Series"]:
                        if serie["Level"] == (level - 1):
                            player = all_players.pop(0)
                            serie["Teams"][i]["Players"] = player["Players"]
                            serie["InProgress"] = True
                    all_players.reverse()
                    if i%2 == 1:
                        matches_data["Series"].reverse()
                if matches_data["Series"][0]["Name"] == "Final":
                    matches_data["Series"].reverse()

    with open(f"{data_dir}/teams/{sport}_series.json", "w") as file:
        json.dump(matches_data, file, ensure_ascii=False)
    if "Pizza" in sport:
        return
    if serie_to_update == "Final" and server_serie["Over"]:
        teams: dict = dict(Teams=[])
        for team in server_serie["Teams"]:
            if team["rank"]:
                if team["rank"] <= server_serie["Selected"]:
                    teams["Teams"].append(team)
        add_new_results(sport, teams, data_dir)
    logger.info("update_list end")

    """
            level = player_data["level"]
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

    """

def update_seeding(sport: str, data: dict, data_dir: str) -> None:
    pass


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
    update_global_bets_results(data_dir)
    update_global_results(data_dir)


def generate_vote_results(data_dir: str, sportname: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info("generate_vote_results")
    players_score: list = []
    with open(f"{data_dir}/teams/{sportname}_votes.json") as f:
        matches_data = json.load(f)
        serie = matches_data
        logger.info(f"Raw data is{serie}")
        for player in serie["Teams"]:
            score = len(player["votes"])
            players_score.append(dict(Players=player["Players"], score=score))
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

    year = str(datetime.date.today().year)
    data = dict()
    if os.path.exists("{data_dir}/results/sports/{sportname}_votes_summary.json"):
        with open(
            f"{data_dir}/results/sports/{sportname}_votes_summary.json", "r"
        ) as file:
            data = json.load(file)
    data[year] = dict(Teams=players_score)
    with open(f"{data_dir}/results/sports/{sportname}_votes_summary.json", "w") as file:
        json.dump(data, file, ensure_ascii=False)
    logger.info("generate_votes_results end")


def get_results(athlete: Any, data_dir: str) -> dict:
    logger = logging.getLogger(__name__)
    #logger.info("get_results")
    results: dict = dict(nr1=[], nr2=[], nr3=[])
    for filename in os.listdir(f"{data_dir}/results/sports/"):
        #logger.info(f"{filename}")
        if "_summary.json" in filename:
            sport = filename.replace("_summary.json", "")
            with open(f"{data_dir}/results/sports/{filename}", "r") as file:
                current_year = str(datetime.date.today().year)
                sport_results = json.load(file)
                if current_year in sport_results:
                    for team in sport_results[current_year]["Teams"]:
                        if re.search(f"\\b{athlete}\\b", team["Players"]):
                            rank = team["rank"]
                            if rank < 4:
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
            if os.path.exists(f"{data_dir}/bets/{sport}.json"):
                with open(f"{data_dir}/results/sports/{filename}", "r") as file:
                    current_year = str(datetime.date.today().year)
                    sport_results = json.load(file)
                    logger.debug(f"All sport result : {sport_results}")
                    if current_year in sport_results:
                        for team in sport_results[current_year]["Teams"]:
                            logger.info(f"Team is {team}")

                            if (
                                team["rank"] == 1
                                or team["rank"] == 2
                                or team["rank"] == 3
                            ):
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
    for athlete in players_list(data_dir):
        logger.info(f"Update player {athlete}")
        result = update_results(athlete, data_dir)
        result["name"] = athlete
        results.append(result)
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
    for athlete in players_list(data_dir):
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


def end_rangement(data_dir: str) -> None:
    with open(f"{data_dir}/teams/Rangement.json", "r") as file:
        data = json.load(file)
    players = data["Players"]
    players = sorted(players, key=lambda i: i["score"])
    players.reverse()
    print(players)
    max_score = players[0]["score"]
    rank = 1
    for player in players:
        if player["score"] == max_score:
            player["rank"] = rank
        else:
            max_score = player["score"]
            rank += 1
            if rank == 4:
                break
            player["rank"] = rank

    teams: dict = dict(Teams=[])
    for team in players:
        if "rank" in team:
            teams["Teams"].append(dict(rank=team["rank"], Players=team["name"]))
    add_new_results("Rangement", teams, data_dir)
