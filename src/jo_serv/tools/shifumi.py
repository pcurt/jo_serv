import json
import logging
import math
import time
from enum import Enum
from typing import Any

from jo_serv.server.server import shifumi_presence, shifumi_scores, shifumi_status

GAMESTATUS = Enum("GAMESTATUS", ["INIT", "COUNTDOWN", "INPROGRESS"])
VOTING_CD = 10


def shifumi_process(data_dir: str) -> None:
    """This process handles shifumi"""
    logger = logging.getLogger(__name__)
    logger.info("Shifumi process start")
    game_status = GAMESTATUS.INIT
    party_id = math.floor(time.time())
    first_time = True
    tour = 0
    leaver = []
    while True:
        time.sleep(1)
        shifumi_presence.acquire()
        data = json.load(open(data_dir + "/teams/shifumi.json", "r"))
        shifumi_presence.release()
        # logger.info(game_status)
        shifumi_status.acquire()
        try:
            data_status = json.load(open(data_dir + "/teams/shifumi_status.json", "r"))
            winner = data_status.get("lastwinner")
            previous_active_players = data_status.get("active_players")
        except Exception:
            logger.info("Exception in shifumi.py")
            winner = "Whisky"
            previous_active_players = []
        if first_time:  # if a game wasn't already started, we add all new players
            active_players = []
            players_and_sign = []
            for player, params in data.items():
                if params.get("sign") != "puit" and time.time() - 2 < params.get(
                    "time"
                ):
                    active_players.append(player)
                    players_and_sign.append((player, params.get("sign")))
        else:  # else we finish the game.
            active_players = previous_active_players
            players_and_sign = []
            for player in previous_active_players:
                if data.get(player) is not None:
                    if time.time() - 2 > data.get(player).get("time"):
                        active_players.remove(player)
                        logger.info(f"{player} left!")
                        leaver.append(player)
                    elif data.get(player).get("sign") != "puit":
                        players_and_sign.append((player, data.get(player).get("sign")))

                else:
                    active_players.remove(player)
                    logger.info(f"{player} left!")
                    leaver.append(player)
        if len(players_and_sign) > 1:
            # game will start
            if game_status == GAMESTATUS.INIT:
                votingtick = math.floor(time.time()) + VOTING_CD
                game_status = GAMESTATUS.COUNTDOWN
            elif game_status == GAMESTATUS.INPROGRESS:
                players_who_played = [x[0] for x in players_and_sign]
                all_players_voted = False
                for player in active_players:
                    if player not in players_who_played:
                        all_players_voted = False
                        break
                    else:
                        all_players_voted = True
                if all_players_voted:
                    votingtick = math.floor(time.time()) + VOTING_CD
                    game_status = GAMESTATUS.COUNTDOWN
                    logger.info("all players voted! lol")
            else:
                if votingtick == math.floor(time.time()):
                    logger.info("Voting!")
                    winner = vote_match(players_and_sign)
                    logger.info(winner)
                    first_time = False
                    tour += 1
                    if type(winner) == list:
                        active_players = winner
                        leaver = []
                        if len(active_players) == 1:
                            winner = winner[0]
                            party_id = math.floor(time.time())
                            first_time = True
                            tour = 0
                        else:
                            winner = "Whisky"
                            logger.info("game_status in progress")
                            game_status = GAMESTATUS.INPROGRESS
                    else:
                        leaver = []
                        game_status = GAMESTATUS.INIT
                        if winner != "draw":
                            party_id = math.floor(time.time())
                            first_time = True
                            tour = 0
                            shifumi_scores.acquire()
                            scores = json.load(
                                open(data_dir + "/teams/shifumi_scores.json", "r")
                            )
                            if scores.get(winner) is not None:
                                scores[winner] = int(scores.get(winner)) + 1
                            else:
                                scores[winner] = 1
                            json.dump(
                                scores,
                                open(data_dir + "/teams/shifumi_scores.json", "w"),
                            )
                            shifumi_scores.release()
                        else:
                            game_status = GAMESTATUS.INPROGRESS
                            logger.info("Draw so no winner yet")
        elif len(active_players) < 2:
            game_status = GAMESTATUS.INIT
            votingtick = -1
            first_time = True
            tour = 0
        json.dump(
            dict(
                votingtick=votingtick,
                lastwinner=winner,
                party_id=party_id,
                active_players=active_players,
                game_in_progress=not first_time,
                tour=tour,
                leaver=leaver,
            ),
            open(data_dir + "/teams/shifumi_status.json", "w"),
        )
        shifumi_status.release()


def vote_match(players: list) -> Any:
    """players and match"""
    if len(players) == 2:
        # finale directe:
        player0, sign0 = players[0]
        player1, sign1 = players[1]
        if sign0 == sign1:
            return "draw"
        if (
            (sign0 == "Ciseaux" and sign1 == "Papier")
            or ((sign0 == "Pierre" and sign1 == "Ciseaux"))
            or (sign0 == "Papier" and sign1 == "Pierre")
        ):
            return player0
        else:
            return player1
    else:
        signs = [x[1] for x in players]
        # si 3 signes different, c'est draw
        if "Pierre" in signs and "Ciseaux" in signs and "Papier" in signs:
            return "draw"
        one_sign_different = False

        for sign in signs:
            if sign != signs[0]:
                one_sign_different = True
        if not one_sign_different:
            # tout le monde a joué le meme signe
            return "draw"

        winning_sign = "puit"
        if "Pierre" in signs and "Ciseaux" in signs:
            winning_sign = "Pierre"
        if "Pierre" in signs and "Papier" in signs:
            winning_sign = "Papier"
        if "Ciseaux" in signs and "Papier" in signs:
            winning_sign = "Ciseaux"
        winning_players = []
        for player, sign in players:
            if sign == winning_sign:
                winning_players.append(player)
        return winning_players
