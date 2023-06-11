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
GAMESTATUS =  Enum("GAMESTATUS", ["INIT", "COUNTDOWN", "FINISHED"])
def shifumi_process(data_dir: str) -> None:
    """ This process handles shifumi"""
    logger = logging.getLogger(__name__)
    logger.info("Shifumi process start")
    game_status = GAMESTATUS.INIT
    while True:
        time.sleep(1)
        shifumi_presence.acquire()
        data = json.load(open(data_dir + "/teams/shifumi.json", "r"))
        shifumi_presence.release()
        active_players = []
        for player, params in data.items():
            logger.info(active_players)
            if params.get("sign") != "puit":
                active_players.append((player, params.get("sign")))
        logger.info(game_status)
        shifumi_status.acquire()
        data = json.load(open(data_dir + "/teams/shifumi_status.json", "r"))
        winner = data.get("lastwinner")
        if len(active_players) > 1:
            # game will start
            if game_status == GAMESTATUS.INIT:
                votingtick = math.floor(time.time()) + 10
                game_status = GAMESTATUS.COUNTDOWN
            else:
                if votingtick == math.floor(time.time()):
                    logger.info("Voting!")
                    winner = vote_match(active_players)
                    logger.info(winner)
                    game_status = GAMESTATUS.INIT
        else:
            game_status = GAMESTATUS.INIT
            votingtick = -1
        json.dump(dict(votingtick=votingtick, lastwinner=winner), open(data_dir + "/teams/shifumi_status.json", "w"))
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

    # for player, sign in active_players