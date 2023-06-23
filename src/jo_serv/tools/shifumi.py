import hashlib
import json
import logging
import math
import os
import shutil
import time
from enum import Enum

from jo_serv.server.server import shifumi_presence, shifumi_status

GAMESTATUS = Enum("GAMESTATUS", ["INIT", "COUNTDOWN", "INPROGRESS"])


def shifumi_process(data_dir: str) -> None:
    """This process handles shifumi"""
    logger = logging.getLogger(__name__)
    logger.info("Shifumi process start")
    game_status = GAMESTATUS.INIT
    party_id = math.floor(time.time())
    first_time = True
    tour = 0
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
            previous_vote = data_status.get("votingtick")
        except:
            logger.info("Exception in shifumi.py")
            winner = "Whisky"
            previous_active_players = []
            previous_vote = -1
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
                    elif (
                        data.get(player).get("sign") != "puit"
                        and data.get(player).get("time") > previous_vote + 2
                    ):
                        players_and_sign.append((player, data.get(player).get("sign")))
                else:
                    active_players.remove(player)
                    logger.info(f"{player} left!")
        logger.info(active_players)
        logger.info(players_and_sign)
        logger.info(game_status)
        if len(players_and_sign) > 1:
            # game will start
            if game_status == GAMESTATUS.INIT:
                votingtick = math.floor(time.time()) + 2
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
                    votingtick = math.floor(time.time()) + 2
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
                        game_status = GAMESTATUS.INIT
                        if winner != "draw":
                            party_id = math.floor(time.time())
                            first_time = True
                            tour = 0
        elif len(active_players) < 2:
            game_status = GAMESTATUS.INIT
            votingtick = -1
            first_time = True
            tour = 0
            logger.info("Reseting game")
        json.dump(
            dict(
                votingtick=votingtick,
                lastwinner=winner,
                party_id=party_id,
                active_players=active_players,
                game_in_progress=not first_time,
                tour=tour,
            ),
            open(data_dir + "/teams/shifumi_status.json", "w"),
        )
        shifumi_status.release()


def vote_match(players):
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
