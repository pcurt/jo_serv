import hashlib
import json
import logging
import os
import shutil
import time
import math
from enum import Enum
from jo_serv.server.server import (
    shifumi_presence,
    shifumi_status

)
GAMESTATUS =  Enum("GAMESTATUS", ["INIT", "COUNTDOWN", "INPROGRESS"])
def shifumi_process(data_dir: str) -> None:
    """ This process handles shifumi"""
    logger = logging.getLogger(__name__)
    logger.info("Shifumi process start")
    game_status = GAMESTATUS.INIT
    party_id = math.floor(time.time())
    first_time = True
    while True:
        time.sleep(1)
        shifumi_presence.acquire()
        data = json.load(open(data_dir + "/teams/shifumi.json", "r"))
        shifumi_presence.release()
        logger.info(game_status)
        shifumi_status.acquire()
        data_status = json.load(open(data_dir + "/teams/shifumi_status.json", "r"))
        winner = data_status.get("lastwinner")
        if first_time: # if a game wasn't already started, we add all new players
            active_players = []
            players_and_sign = []
            for player, params in data.items():
                if params.get("sign") != "puit":
                    logger.info("keepo")
                    active_players.append(player)
                    players_and_sign.append((player, params.get("sign")))
        else: # else we finish the game.
            players_and_sign = []
            active_players = data_status.get("active_players")
            for player in active_players:
                if data.get(player) is not None:
                    if data.get(player).get("sign") != "puit":
                        players_and_sign.append((player, data.get(player).get("sign")))
                else:
                    logger.info("Someone left!")
                    game_status = GAMESTATUS.INIT
                    votingtick = -1
        if len(players_and_sign) > 1:
            # game will start
            if game_status == GAMESTATUS.INIT:
                votingtick = math.floor(time.time()) + 10
                game_status = GAMESTATUS.COUNTDOWN
            else:
                if votingtick == math.floor(time.time()):
                    logger.info("Voting!")
                    winner = vote_match(players_and_sign)
                    logger.info(winner)
                    game_status = GAMESTATUS.INIT
                    first_time = False
                    if winner != "draw":
                        party_id = math.floor(time.time())
                        first_time = True
        else:
            game_status = GAMESTATUS.INIT
            votingtick = -1
        logger.info("ici")
        json.dump(dict(votingtick=votingtick, lastwinner=winner, party_id=party_id, active_players=active_players), open(data_dir + "/teams/shifumi_status.json", "w"))
        shifumi_status.release()

def vote_match(players):
    """ players and match"""
    if len(players) == 2:
        # finale directe:
        player0, sign0 = players[0]
        player1, sign1 = players[1]
        if sign0 == sign1:
            return "draw"
        if (sign0 == "Ciseaux" and sign1 == "Papier") \
            or ((sign0 == "Pierre" and sign1 == "Ciseaux")) \
                or (sign0 == "Papier" and sign1 == "Pierre"):
            return player0
        else:
            return player1
    else:
        signs = [x[1] for x in players]
        if "Pierre" in signs and "Ciseaux" in signs and "Papier" in signs:
            return "draw"