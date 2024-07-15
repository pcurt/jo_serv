# Standard lib imports
import datetime
import hashlib
import json
import logging
import os
import random
import re
import time
from threading import Lock
from typing import Any

import requests  # type: ignore
from flask import Flask, Response, make_response, request, send_file  # type: ignore
from jo_serv.tools.killer import (
    assign_kill,
    change_mission,
    count_still_alive,
    end_killer,
    find_killer_index,
    find_player_index,
    generate_killer,
    generate_killer_results,
    get_killer_data,
    get_mission,
    get_killer_player_info,
    kill_player,
    killer_players,
    save_killer_data,
    switch_state_killer,
    update_missions,
    )

from jo_serv.tools.excel_mgmt import (
    generate_pools,
    generate_series,
    generate_table,
    get_sport_config,
)

from jo_serv.tools.tools import (
    adapt_bet_file,
    generate_can_be_added_list,
    generate_event_list,
    get_palmares,
    players_list,
    send_notif,
    toggle_lock_bets,
    update_bet_file,
    user_is_authorized,
)

from jo_serv.tools.match_mgmt import (
    end_rangement,
    generate_vote_results,
    lock,
    team_to_next_step,
    unlock,
    update_global_results,
    update_list,
    update_playoff_match,
    update_poules_match,
    update_vote,

)

CANVA_SIZE = 50
MAX_NUMBER_CANVA = 500
live_update_mutex = Lock()
shifumi_presence = Lock()
shifumi_status = Lock()
shifumi_scores = Lock()
png_mutex = Lock()
size_mutex = Lock()
connection_mutex = Lock()
canva_array_mutex = [Lock()] * MAX_NUMBER_CANVA
killer_mutex = Lock()
rangement_mutex = Lock()
PARTY_STATUS = "NOT_STARTED"


def create_server(data_dir: str) -> Flask:
    """Create the server

    Args:
        data_dir (str): Path to data directory

    Returns:
        Flask: The server
    """
    data_dir = data_dir
    logger = logging.getLogger(__name__)
    logger.info("Create the server")
    app = Flask(__name__)

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Response:
        """Login page

        Returns:
            Response: 200 if login is success
        """
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)

        rcv_user = json_data["username"]
        rcv_password = json_data["password"]

        logger.info(f" User {rcv_user} is trying to login")

        f = open(data_dir + "/login.json", "r")
        data = json.load(f)

        for user in data["users"]:
            if rcv_user == user["username"]:
                if user["password"] == rcv_password:
                    logger.info("Log success")
                    return Response(response="Logged IN ", status=200)
                else:
                    logger.info("Log failed")
                    return Response(response="Wrong password ", status=403)

        return Response(response="Wrong user ", status=403)

    @app.route("/Chatalere/<path:name>", methods=["GET", "POST"])
    def chat(name: str) -> Response:
        """Chat endpoints

        Returns:
            Response: The chat file content
        """
        if request.method == "GET":
            logger.debug(f"Get on /Chatalere/{name}")
            path = data_dir + "/chat/" + name
            if os.path.exists(path):
                with open(path, "rb") as file:
                    logger.debug(f"Read files {path}")
                    return Response(response=file.read(), status=200)
            return Response(response="No such file", status=404)
        if request.method == "POST":
            logger.info(f"Post on /chat/{name}")
            decode_data = request.data.decode("utf-8")
            logger.info(f"Decode data: {decode_data}")
            json_data = json.loads(decode_data)
            username = json_data.get("username")
            # sportname = json_data.get("sportname")
            text = json_data.get("text")
            if text == "" or username == "":
                return Response(response="fdp", status=200)
            now = datetime.datetime.now()
            with open(f"{data_dir}/chat/{name}", "a") as new_file:
                new_file.write(
                    "\n"
                    + now.strftime("%m/%d, %H:%M")
                    + "  -  "
                    + username
                    + " : "
                    + text
                )
                return Response(response="fdp", status=200)

        logger.error(f"Error reading files {path}")
        return Response(response="Error on endpoint Chatalere", status=404)

    @app.route("/teams/<path:name>", methods=["GET", "POST"])
    def teams(name: str) -> Response:
        """Teams endpoints

        Returns:
            Response: The teams file content
        """
        if request.method == "GET":
            logger.info(f"Get on /teams/{name}")
            path = data_dir + "/teams/" + name
            if os.path.exists(path):
                with open(path, "rb") as file:
                    return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint teams", status=404)

    @app.route("/results/<path:name>", methods=["GET", "POST"])
    def results(name: str) -> Response:
        """Results endpoints

        Returns:
            Response: the asked result content
        """
        if request.method == "GET":
            logger.info(f"Get on /results/{name}")
            path = data_dir + "/results/" + name
            if os.path.exists(path):
                with open(path, "rb") as file:
                    return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint teams", status=404)

    @app.route("/athletes/<path:name>", methods=["GET", "POST"])
    def athletes(name: str) -> Response:
        """athletes endpoints

        Returns:
            Response: the asked athletes content
        """
        if request.method == "GET":
            logger.info(f"Get on /athletes/{name}")
            path = data_dir + "/athletes/" + name
            if os.path.exists(path):
                with open(path, "rb") as file:
                    return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint teams", status=404)

    @app.route("/pushtoken", methods=["POST"])
    def pushtoken() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")

        if json_data.get("token"):
            if not os.path.exists(data_dir + "/tokens.txt"):
                open(data_dir + "/tokens.txt", "w")
            if (
                json_data.get("token") not in open(data_dir + "/tokens.txt", "r").read()
            ):  # just to be sure we don't write again the same
                if json_data.get("username"):
                    open(data_dir + "/tokens.txt", "a").write(
                        json_data.get("token") + ":" + json_data.get("username") + "\n"
                    )
                else:
                    open(data_dir + "/tokens.txt", "a").write(
                        json_data.get("token") + ":\n"
                    )
            elif json_data.get("username") != "":
                lines = open(data_dir + "/tokens.txt", "r").readlines()
                for local_token in lines:
                    if json_data.get("token") in local_token:
                        if (
                            json_data.get("username")
                            != local_token.split(":")[-1].replace("\n", "")
                            and json_data.get("username") != ""
                        ):
                            logger.info("This token changed login!")
                            to_update = True
                            break
                        else:
                            to_update = False
                            logger.info("I know already this token")
                if to_update:
                    raw_txt = open(data_dir + "/tokens.txt", "r").read()
                    logger.info("(" + json_data.get("token") + ".*)")
                    regexp = re.findall(
                        "(" + re.escape(json_data.get("token")) + ".*)", raw_txt
                    )[0]
                    raw_txt = raw_txt.replace(
                        regexp,
                        json_data.get("token") + ":" + json_data.get("username") + "\n",
                    )
                    open(data_dir + "/tokens.txt", "w").write(raw_txt)
        return Response(response="fdp", status=200)

    @app.route("/cluedo", methods=["POST"])
    def cluedo() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")
        username = json_data.get("cluedo")

        if os.path.exists(data_dir + "/lasttimecluedo"):
            last_time = float(open(data_dir + "/lasttimecluedo", "r").read())
        else:
            last_time = time.time() - 16 * 60
        if time.time() > (last_time + 15 * 60):  # filter 15 mins
            since = last_time - time.time()
            logger.info(f"cluedotime no cluedo since {since} s")
            open(data_dir + "/lasttimecluedo", "w").write(str(time.time()))
            tokens = open(data_dir + "/tokens.txt", "r").readlines()
            for token in tokens:
                if "ExponentPushToken" in token:
                    data = {
                        "to": token.split(":")[0].replace(":", ""),
                        "title": "CLUEDO!",
                        "body": "Demandé par : %s" % username,
                    }
                    req = requests.post(
                        "https://exp.host/--/api/v2/push/send", data=data
                    )
                    if re.findall("DeviceNotRegistered", req.text):
                        logger.info(
                            "device not registered anymore so removing the line"
                        )
                        full_txt = open(data_dir + "/tokens.txt", "r").read()
                        open(data_dir + "/tokens.txt", "w").write(
                            full_txt.replace(token, "")
                        )
        else:
            logger.info("ignore as it's less than 15 mins since last")
        return Response(response="fdp", status=200)

    @app.route("/pushnotif", methods=["POST"])
    def pushnotif() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")
        to_req = json_data.get("to")
        title = json_data.get("title")
        body = json_data.get("body")

        send_notif(to_req, title, body, data_dir)
        return Response(response="fdp", status=200)

    @app.route("/pushmatch", methods=["POST"])
    def pushmatch() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")
        username = json_data.get("username")
        sport = json_data.get("sport")
        match = json_data.get("match")
        type = json_data.get("type")

        if user_is_authorized(username, sport, data_dir):
            logger.info("User is authorized")
            logger.info(f"Type is {type}")
            if type == "playoff":
                match_id = int(match["uniqueId"])
                logger.info(f"update_playoff {sport}, {match_id}, {match}, {data_dir}")
                update_playoff_match(sport, match_id, match, data_dir)
                logger.info("update_playoff_match")
            elif type == "poules":
                match_id = int(match["uniqueId"])
                update_poules_match(sport, match_id, match, data_dir)
            elif type == "liste":
                update_list(sport, match, data_dir)
        else:
            logger.info("User in not authorized")
        logger.info("update_global_results")
        update_global_results(data_dir)
        logger.info("Match is pushed")

        # fix_json() # FIXME to delete ?
        # log(sport, username, data) # FIXME to delete ?
        return Response(response="fdp", status=200)

    @app.route("/pushvote", methods=["POST"])
    def pushvote() -> Response:
        """Push pizza endpoints

        Returns:
            Response: The operation status
        """
        if request.method == "POST":
            logger.info("Post on /pushpizza")
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            username = json_data.get("username")
            vote = json_data.get("vote")
            sport = json_data.get("sportname")

            update_vote(
                data_dir=data_dir, username=username, vote=vote, sportname=sport
            )
            generate_vote_results(data_dir, sport)

            return Response(response="fdp", status=200)
        return Response(response="Error on endpoint pushpizza", status=404)

    @app.route("/updateTeams", methods=["POST"])
    def updateTeams() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")
        sport = json_data.get("sport")
        teams = json_data.get("teams")
        arbitre = json_data.get("arbitre")

        new_teams = []
        for team in teams:
            if team["username"] != "":
                new_teams.append(dict(Players=team["username"]))
        file_name = f"{sport}.json"
        logger.info(f"file name is {file_name}")
        with open(f"{data_dir}/teams/{file_name}", "w") as file:
            json.dump(dict(Teams=new_teams), file, ensure_ascii=False)
        logger.info("teams updated")
        sport_config = get_sport_config(file_name, data_dir)
        if sport_config["Type"] == "Table":
            table = generate_table(new_teams, sport_config["Teams per match"])
            file_name = f"{sport}_playoff.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(table, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/save/{file_name}", "w") as file:
                json.dump(table, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/{file_name}", "r") as file:
                data = json.load(file)
            matches = data["matches"]
            for match in matches:
                if match["over"]:
                    team_to_next_step(sport, match["uniqueId"], data_dir)
            logger.info("Playoff renewed")

        elif sport_config["Type"] == "Pool":
            pools = generate_pools(new_teams)
            file_name = f"{sport}_poules.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(pools, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/save/{file_name}", "w") as file:
                json.dump(pools, file, ensure_ascii=False)
            logger.info("Pools renewed")

        elif sport_config["Type"] == "Series":
            series = generate_series(new_teams, sport_config)
            file_name = f"{sport}_series.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/save/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
            logger.info("Series renewed")

        file_name = f"{sport}_status.json"
        with open(f"{data_dir}/teams/{file_name}", "r") as file:
            data = json.load(file)
        data["arbitre"] = []
        for new_arbitre in arbitre:
            if new_arbitre != "" and new_arbitre not in data["arbitre"]:
                data["arbitre"].append(new_arbitre)
        with open(f"{data_dir}/teams/{file_name}", "w") as file:
            json.dump(data, file, ensure_ascii=False)
        adapt_bet_file(data_dir, sport)
        for player in players_list(data_dir):
            generate_event_list(player, data_dir)
        generate_can_be_added_list(sport, data_dir)
        os.system(f"cp {data_dir}/teams/{sport}*.json {data_dir}/teams/save/")
        return Response(response="fdp", status=200)

    @app.route("/bets/<path:name>", methods=["GET", "POST"])
    def bets(name: str) -> Response:
        """Bets endpoints

        Returns:
            Response: The bet file content
        """
        if request.method == "GET":
            logger.info(f"Get on /bets/{name}")
            path = data_dir + "/bets/" + name
            if os.path.exists(path):
                with open(path, "rb") as file:
                    return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint bets", status=404)

    @app.route("/pushBets", methods=["POST"])
    def pushBets() -> Response:
        """Push bets endpoints

        Returns:
            Response: The operation status
        """
        if request.method == "POST":
            logger.info("Post on /pushBets")
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            username = json_data.get("username")
            sport = json_data.get("sport")
            bets = json_data.get("bets")
            update_bet_file(
                data_dir=data_dir, username=username, sport=sport, bets=bets
            )
            return Response(response="fdp", status=200)
        return Response(response="Error on endpoint pushBets", status=404)

    @app.route("/lockBets", methods=["POST"])
    def lockBets() -> Response:
        """Lock bets endpoints

        Returns:
            Response: The operation status
        """
        if request.method == "POST":
            logger.info("Post on /lockBets")
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            sport = json_data.get("sport")
            toggle_lock_bets(sport, data_dir)
            return Response(response="fdp", status=200)
        return Response(response="Error on endpoint pushBets", status=404)

    @app.route("/locksport", methods=["POST"])
    def locksport() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")

        sport = json_data.get("sport")
        type = json_data.get("type")

        if type == "lock":
            lock(sport, data_dir)
        elif type == "unlock":
            unlock(sport, data_dir)

        return Response(response="fdp", status=200)

    @app.route("/canvalive", methods=["GET"])
    def canvalive() -> Response:
        live_update_mutex.acquire()
        try:
            with open(f"{data_dir}/teams/canva/live_update.json", "r") as file:
                live_data = json.load(file)
        finally:
            live_update_mutex.release()
        return make_response(dict(live=live_data))

    # todo: endpoint enlarge must change global variable line/col

    @app.route("/canvasetcolor", methods=["POST"])
    def canvasetcolor() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        live_update_mutex.acquire()
        try:
            with open(f"{data_dir}/teams/canva/live_update.json", "r") as file:
                live_update = json.load(file)
            live_update.append(json_data)
            with open(f"{data_dir}/teams/canva/live_update.json", "w") as file:
                json.dump(live_update, file)
        finally:
            live_update_mutex.release()
        logger.info(f"Data received : {decode_data}")
        id = int(json_data.get("id"))
        size_mutex.acquire()
        try:
            size_json = json.load(open(f"{data_dir}/teams/canva/sizecanva.json", "r"))
        finally:
            size_mutex.release()
        col_nb = int(size_json.get("cols"))
        if int(json_data.get("cols")) != col_nb:
            return Response(response="Wrong col numbers", status=403)
        line_nb = int(size_json.get("lines"))
        if int(json_data.get("lines")) != line_nb:
            return Response(response="Wrong line numbers", status=403)
        pixel_per_line = col_nb  # todo: configurable
        number_of_tile_x = col_nb / CANVA_SIZE  # 200/50
        x_coord = int(id % pixel_per_line / CANVA_SIZE)
        y_coord = int(id / pixel_per_line / CANVA_SIZE)
        canva_number = int(x_coord + y_coord * number_of_tile_x)
        canva_array_mutex[canva_number].acquire()
        try:
            if id >= 0:
                x = id % CANVA_SIZE
                y = int(id / pixel_per_line)  # line in absolute
                id = x + (y % CANVA_SIZE) * CANVA_SIZE
                color = json_data.get("color")
                username = json_data.get("username")
                if not os.path.exists(
                    f"{data_dir}/teams/canva/canva{canva_number}.json"
                ):
                    return Response(response="wrongid", status=404)
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.json", "r"
                ) as file:
                    data = json.load(file)
                    data[id]["color"] = color
                    data[id]["name"] = username
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.json", "w"
                ) as file:
                    json.dump(data, file)
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.json", "r"
                ) as file:
                    raw_txt = file.read()
                m = hashlib.sha256()
                m.update(str.encode(raw_txt))
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.sha256", "w"
                ) as file:
                    file.write(m.hexdigest())
                return Response(response="fdp", status=200)
            else:
                return Response(response="wrongid", status=403)
        except Exception as e:
            logger.info(f"issue in canvasetcolor {e}")
        finally:
            canva_array_mutex[canva_number].release()
            return Response(response="fdp", status=200)

    @app.route("/canvausername/<path:localid>", methods=["GET"])
    def canvausername(localid: int) -> Response:
        logger.info("Get on : /canvausername")
        if request.method == "GET":
            id = int(localid)
            if id >= 0:
                size_mutex.acquire()
                try:
                    size_json = json.load(
                        open(f"{data_dir}/teams/canva/sizecanva.json", "r")
                    )
                finally:
                    size_mutex.release()
                col_nb = size_json.get("cols")
                pixel_per_line = col_nb  # todo: configurable
                number_of_tile_x = pixel_per_line / CANVA_SIZE
                x_coord = int(id % pixel_per_line / CANVA_SIZE)
                y_coord = int(id / pixel_per_line / CANVA_SIZE)
                canva_number = int(x_coord + y_coord * number_of_tile_x)
                x = id % CANVA_SIZE
                y = int(id / pixel_per_line)  # line in absolute
                id = x + (y % CANVA_SIZE) * CANVA_SIZE
                logger.info(f"{id}, {canva_number}, {localid}")
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.json", "r"
                ) as file:
                    data = json.load(file)
                    username = data[id]["name"]
                    response = make_response(username)
                    response.headers["Content-length"] = str(len(username))
                    return response
        return Response(response="wrongid", status=404)

    @app.route("/canvasizedev", methods=["GET"])
    def canvasizedev() -> Response:
        logger.info("Get on : /canvasizedev")
        if request.method == "GET":
            size_mutex.acquire()
            try:
                size_json = json.load(
                    open(f"{data_dir}/teams/canva/sizecanva.json", "r")
                )
            finally:
                size_mutex.release()
            resp = dict(lines=size_json.get("lines"), cols=size_json.get("cols"))
            return make_response(resp)

        return Response(response="Error on endpoint canva", status=404)

    @app.route("/canvadev", methods=["GET"])
    def canvadev() -> Any:
        logger.info("Get on : /canvadev")
        if request.method == "GET":
            try:
                if png_mutex.locked():
                    resp = send_file(
                        f"{data_dir}/teams/canva/canva2.png", mimetype="image/png"
                    )
                else:
                    resp = send_file(
                        f"{data_dir}/teams/canva/canva.png", mimetype="image/png"
                    )
            except Exception as e:
                logger.error(f"Error in sending image {e}")
                resp = Response(response="Error on endpoint canva", status=404)
            finally:
                return resp
        return Response(response="Error on endpoint canva", status=404)

    @app.route("/photo/<path:name>", methods=["GET"])
    def photo(name: str) -> Any:
        logger.info(f"Get on : /photo for {name}")
        try:
            resp = send_file(f"{data_dir}/photos/{name}.jpeg", mimetype="image/jpeg")
            return resp
        except Exception:
            return Response(response="Can't find requested photo", status=404)

    @app.route("/killer-start", methods=["POST"])
    def killer_start() -> Response:
        logging.info("Call on start killer")
        try:
            killer_mutex.acquire()
            if generate_killer(data_dir):
                killer_mutex.release()
                return Response(response="Game started", status=200)
            killer_mutex.release()
            return Response(response="Can't start killer", status=404)
        except Exception:
            killer_mutex.release()
            return Response(response="Can't start killer", status=404)

    @app.route("/killer-end", methods=["POST"])
    def killer_end() -> Response:
        logging.info("Call on end killer")
        try:
            killer_mutex.acquire()
            data = get_killer_data(data_dir)
            data["over"] = True
            save_killer_data(data_dir, data)
            generate_killer_results(data_dir, False)
            killer_mutex.release()
            return Response(response="Killer over", status=200)
        except Exception:
            killer_mutex.release()
            return Response(response="Can't stop killer", status=404)

    @app.route("/killer-update-missions", methods=["POST"])
    def killer_update_missions() -> Response:
        logging.info("Call on update missions killer")
        try:
            killer_mutex.acquire()
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            missions = json_data["missions"]
            update_missions(data_dir, missions)
            killer_mutex.release()
            return Response(response="Missions updated", status=200)
        except Exception:
            killer_mutex.release()
            return Response(response="Can't update missions", status=404)

    @app.route("/killer-register", methods=["POST"])
    def killer_register() -> Response:
        logging.info("Call on killer register")
        try:
            killer_mutex.acquire()
            data = get_killer_data(data_dir)
            if data["started"]:
                raise
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            registering = json_data["registering"]
            name = json_data["name"]
            switch_state_killer(data_dir, name, registering)
            killer_mutex.release()
            return Response(response="Succesfully changed registration", status=200)
        except Exception:
            killer_mutex.release()
            return Response(response="Can't change registration", status=404)

    @app.route("/killer-change-mission", methods=["POST"])
    def killer_change_mission() -> Response:
        logging.info("Call on change mission")
        try:
            killer_mutex.acquire()
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            name = json_data["name"]
            mission = json_data["mission"]
            player_index = find_player_index(data_dir, name)
            change_mission(data_dir, player_index, mission)
            killer_mutex.release()
            return Response(response="Mission changed", status=200)
        except Exception:
            killer_mutex.release()
            return Response(response="Can't change player mission", status=404)

    @app.route("/killer-kill", methods=["POST"])
    def killer_kill() -> Response:
        try:
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            name = json_data["name"]
            counter_kill = json_data["counter_kill"]
            give_credit = json_data["give_credit"]
            logging.info(f"Call on kill for {name}")
            if counter_kill:
                logging.info("It's a counter kill")
            killer_mutex.acquire()
            if counter_kill:
                player_index = find_player_index(data_dir, name)
                killer_index = find_killer_index(data_dir, player_index, counter_kill)
                player_mission = get_mission(data_dir, player_index)
                killer_mission = "Contre killer: " + get_mission(data_dir, killer_index)
                change_mission(data_dir, player_index, killer_mission)
                change_mission(data_dir, killer_index, player_mission)
                victim = kill_player(data_dir, player_index)
                assign_kill(data_dir, victim, killer_index)
            else:
                player_index = find_player_index(data_dir, name)
                victim = kill_player(data_dir, player_index)
                if give_credit:
                    killer_index = find_killer_index(data_dir, player_index, counter_kill)
                    assign_kill(data_dir, victim, killer_index)
            if count_still_alive(data_dir) == 1:
                end_killer(data_dir)
        except Exception:
            killer_mutex.release()
            return Response(response="Error on killer", status=404)
        killer_mutex.release()
        return Response(response=f"Killed {name}", status=200)

    @app.route("/killer-info/<path:name>", methods=["GET"])
    def killer_info(name: str) -> Response:
        try:
            killer_mutex.acquire()
            logger.info(f"Get on /killer from user {name}")
            data = get_killer_data(data_dir)
            ret = {
                "started": data["started"],
                "is_alive": True,
                "how_to_kill": "",
                "kills": [],
                "target": "",
                "is_arbitre": False,
                "over": data["over"],
                "lifetime": "",
                "start_date": data["start_date"]
            }
            if data["over"]:
                ret["participants"] = data["participants"]
            elif name not in data["arbitre"]:
                ret["is_playing"] = name in killer_players(data_dir)
                if not data["started"]:
                    with open(data_dir + "/killer/killer_missions.json", "r") as f:
                        ret["missions"] = len(json.load(f))
                    ret["participants"] = killer_players(data_dir)
                else:
                    if not data["over"] and ret["is_playing"]:
                        info = get_killer_player_info(data_dir, name)
                        ret["how_to_kill"] = info["how_to_kill"]
                        ret["is_alive"] = info["is_alive"]
                        ret["kills"] = info["kills"]
                        if not info["is_alive"]:
                            ret["lifetime"] = info["lifetime"]
                        else:
                            ret["target"] = info["target"]
            else:
                ret["is_arbitre"] = True
                if data["started"]:
                    ret["participants"] = data["participants"]
                    random.shuffle(ret["participants"])
                else:
                    ret["participants"] = killer_players(data_dir)
                with open(f"{data_dir}/killer/killer_missions.json", "r") as f:
                    ret["missions"] = json.load(f)
        except Exception:
            killer_mutex.release()
            return Response(response="Error on killer", status=404)
        killer_mutex.release()
        logging.info(ret)
        return Response(response=json.dumps(ret), status=200)

    @app.route("/rangement", methods=["GET"])
    def rangement() -> Response:
        try:
            rangement_mutex.acquire()
            with open(f"{data_dir}/teams/Rangement.json", "r") as file:
                data = json.load(file)
            rangement_mutex.release()
            return Response(response=json.dumps(data), status=200)
        except Exception:
            rangement_mutex.release()
            return Response(response="Error on get rangement", status=404)

    @app.route("/update-rangement", methods=["POST"])
    def update_rangement() -> Response:
        try:
            rangement_mutex.acquire()
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            tasks = json_data.get("tasks")
            tasks_list = []
            for task in tasks:
                if task["title"] != "":
                    tasks_list.append(task)
            with open(f"{data_dir}/teams/Rangement.json", "r") as file:
                data = json.load(file)
            data["tasks"] = tasks_list
            with open(f"{data_dir}/teams/Rangement.json", "w") as file:
                json.dump(data, file)
            rangement_mutex.release()
            return Response(response="ok", status=200)
        except Exception:
            rangement_mutex.release()
            return Response(response="Error on update rangement", status=404)

    @app.route("/update-task", methods=["POST"])
    def update_task() -> Response:
        try:
            rangement_mutex.acquire()
            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            task_to_update = json_data.get("task")
            with open(f"{data_dir}/teams/Rangement.json", "r") as file:
                data = json.load(file)
            tasks_list = data["tasks"]
            busy_people = []
            all_done = True
            for task in tasks_list:
                if task["title"] == task_to_update["title"]:
                    task["state"] = task_to_update["state"]
                    task["participants"] = task_to_update["participants"]
                if task["state"] == 1:
                    for participant in task["participants"]:
                        busy_people.append(participant)
                if task["state"] == 0:
                    task["participants"] = []
                if task["state"] != 2:
                    all_done = False
            for player in data["Players"]:
                player["busy"] = player["name"] in busy_people
                player["score"] = 0
                for task in tasks_list:
                    if task["state"] == 2 and player["name"] in task["participants"]:
                        player["score"] += task["points"] / len(task["participants"])

            logging.info(all_done)
            if all_done:
                data["done"] = True
                end_rangement(data_dir)
            with open(f"{data_dir}/teams/Rangement.json", "w") as file:
                json.dump(data, file)
            rangement_mutex.release()
            return Response(response="ok", status=200)
        except Exception:
            rangement_mutex.release()
            return Response(response="Error on update rangement", status=404)

    @app.route("/shifumi", methods=["POST"])
    def shifumi() -> Response:
        """shifumi endpoints
        Returns:
            Response: The shifumi information
        """

        if request.method == "POST":

            decode_data = request.data.decode("utf-8")
            json_data = json.loads(decode_data)
            username = json_data.get("username")
            sign = json_data.get("sign")
            mobile_party_id = json_data.get("party_id")
            mobile_tour = json_data.get("tour")
            shifumi_status.acquire()
            try:
                status = json.load(open(data_dir + "/teams/shifumi_status.json", "r"))
                voting_in = int(status.get("votingtick")) - time.time()
                last_winner = status.get("lastwinner")
                list_active_players = status.get("active_players")
                party_id = status.get("party_id")
                game_in_progress = status.get("game_in_progress")
                round_in_progress = status.get("round_in_progress")
                tour = status.get("tour")
                leaver = status.get("leaver")
                players_and_sign = status.get("players_and_sign")
            except Exception:
                voting_in = -1
                last_winner = "Whisky"
                list_active_players = []
                party_id = -1
                tour = 0
                game_in_progress = False
                round_in_progress = False
                players_and_sign = []
            finally:
                shifumi_status.release()
            shifumi_scores.acquire()
            scores = json.load(open(data_dir + "/teams/shifumi_scores.json", "r"))
            shifumi_scores.release()
            if list_active_players is None:
                list_active_players = []
            if party_id != mobile_party_id or tour != mobile_tour:
                sign = "puit"
            shifumi_presence.acquire()
            try:
                data = json.load(open(data_dir + "/teams/shifumi.json", "r"))
                data[username] = {"time": time.time(), "sign": sign}

                # Compute the active_players information
                active_players = []

                for player in list_active_players:
                    sign = data.get(player).get("sign")
                    if sign == "puit":
                        has_played = False
                    else:
                        has_played = True
                    active_player = dict(username=player, has_played=has_played)
                    active_players.append(active_player)
                # logger.info(f"active_players : {active_players}")
                # logger.info(f"round_in_progress : {round_in_progress}")

                specs = []
                for player, params in data.items():
                    if time.time() - 2 < params.get("time"):
                        if not game_in_progress:
                            if params.get("sign") == "puit":
                                specs.append(player)
                        else:
                            if player not in list_active_players:
                                specs.append(player)

                json.dump(data, open(data_dir + "/teams/shifumi.json", "w"))
            finally:
                shifumi_presence.release()

            return make_response(
                dict(
                    active_players=active_players,
                    players_and_sign=players_and_sign,
                    specs=specs,
                    voting_in=voting_in,
                    last_winner=last_winner,
                    party_id=party_id,
                    game_in_progress=game_in_progress,
                    round_in_progress=round_in_progress,
                    tour=tour,
                    leaver=leaver,
                    scores=scores,
                )
            )

        return Response(response="Error on shifumi", status=404)

    @app.route("/life", methods=["POST", "GET"])
    def life() -> Response:
        if request.method == "POST":
            decoded_data = json.loads(request.data.decode("utf-8"))
            if "username" not in decoded_data or "screen" not in decoded_data:
                return Response(response="Error on lifestate", status=404)
            username = decoded_data["username"]
            screen = decoded_data["screen"]
            if username == "" or screen == "":
                return Response(response="Error on lifestate", status=404)
            connection_mutex.acquire()
            try:
                with open(f"{data_dir}/connection.json", "r") as file:
                    data = json.load(file)
            finally:
                connection_mutex.release()
            for user in data["users"]:
                if user["name"] == username:
                    user["last_online"] = time.time()
                    user["screen"] = screen
                    try:
                        connection_mutex.acquire()
                        with open(f"{data_dir}/connection.json", "w") as file:
                            json.dump(data, file)
                    finally:
                        connection_mutex.release()

                    return Response(response="Ok", status=200)
            data["users"].append(dict(name=username, last_online=time.time(), screen=screen))
            try:
                connection_mutex.acquire()
                with open(f"{data_dir}/connection.json", "w") as file:
                    json.dump(data, file)
            finally:
                connection_mutex.release()

            return Response(response="Ok", status=200)

        if request.method == "GET":
            try:
                connection_mutex.acquire()
                with open(f"{data_dir}/connection.json", "r") as file:
                    data = json.load(file)
            finally:
                connection_mutex.release()
            online_users = []
            for user in data["users"]:
                if user["last_online"] + 5 > time.time():
                    online_users.append(dict(name=user["name"], screen=user["screen"]))
            return make_response(dict(online=online_users))

        return Response(response="Error on lifestate", status=404)

    @app.route("/annonce", methods=["POST", "GET"])
    def annonce() -> Response:
        if request.method == "POST":
            decoded_data = request.data.decode("utf-8")
            with open(f"{data_dir}/annonce.txt", "w") as file:
                file.write(decoded_data)
            return Response(response="Ok", status=200)

        if request.method == "GET":
            with open(f"{data_dir}/annonce.txt", "r") as file:
                data = file.read()

            return make_response(data)

        return Response(response="Error on annonce", status=404)

    @app.route("/palmares/<path:name>", methods=["GET"])
    def palmares(name: str) -> Any:
        logger.info(f"Get on : /palmares for {name}")
        try:
            return make_response(get_palmares(data_dir, name))
        except Exception:
            return Response(response="Can't find requested palmares", status=404)

    @app.route("/planning", methods=["GET"])
    def planning() -> Any:
        logger.info("Get on : /planning")
        try:
            return send_file(f"{data_dir}/planning.json")
        except Exception:
            return Response(response="Can't find planning", status=404)

    return app
