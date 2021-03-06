# Standard lib imports
import datetime
import hashlib
import json
import logging
import os
import re
import time
from threading import Lock
from typing import Any

import mariadb  # type: ignore
import requests  # type: ignore
from flask import Flask, Response, make_response, request, send_file  # type: ignore

from jo_serv.tools.tools import (
    adapt_bet_file,
    generate_can_be_added_list,
    generate_event_list,
    generate_pizza_results,
    generate_pools,
    generate_series,
    generate_table,
    get_sport_config,
    lock,
    players_list,
    send_notif,
    team_to_next_step,
    toggle_lock_bets,
    unlock,
    update_bet_file,
    update_global_results,
    update_list,
    update_pizza_vote,
    update_playoff_match,
    update_poules_match,
    user_is_authorized,
)

CANVA_SIZE = 50
MAX_NUMBER_CANVA = 500
live_update_mutex = Lock()
png_mutex = Lock()
size_mutex = Lock()
canva_array_mutex = [Lock()] * MAX_NUMBER_CANVA


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

    try:
        conn = mariadb.connect(user="root", database="JO")
        cur = conn.cursor()
        conn.autocommit = True
    except mariadb.Error as e:
        logger.error(f"Error connecting to MariaDB Platform: {e}")

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Response:
        """Login page

        Returns:
            Response: 200 if login is success
        """
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)

        rcv_user = json_data["username"]
        rcv_password = hashlib.sha384(str.encode(json_data["password"])).hexdigest()

        logger.info(f" User {rcv_user} is trying to login")

        try:
            cur.execute("SELECT * from users")
            for (id, user, pwd, autho, date) in cur:
                logger.debug(f"{id} {user} {pwd} {autho} {date}")
                if rcv_user == user:
                    if rcv_password == pwd:
                        logger.info(f"Receive correct password for {user}")
                        return Response(response="Logged IN ", status=200)
                    else:
                        logger.info(f"Receive invalid password for {user}")
        except mariadb.InterfaceError:
            logger.info("Connection to mariadb has been lost, restart the module")
            os._exit(0)

        return Response(response="Wrong password ", status=403)

    @app.route("/Chatalere/<path:name>", methods=["GET", "POST"])
    def chat(name: str) -> Response:
        """Chat endpoints

        Returns:
            Response: The chat file content
        """
        if request.method == "GET":
            logger.info(f"Get on /Chatalere/{name}")
            path = data_dir + "/chat/" + name
            with open(path, "rb") as file:
                logger.info(f"Read files {path}")
                return Response(response=file.read(), status=200)
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
                        "body": "Demand?? par : %s" % username,
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

    @app.route("/pushpizza", methods=["POST"])
    def pushpizza() -> Response:
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

            update_pizza_vote(data_dir=data_dir, username=username, vote=vote)
            generate_pizza_results(data_dir)

            return Response(response="fdp", status=200)
        return Response(response="Error on endpoint pushpizza", status=404)

    @app.route("/updateTeams", methods=["POST"])
    def updateTeams() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        logger.info(f"Data received : {decode_data}")
        sport = json_data.get("sport")
        teams = json_data.get("teams")
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
            file_name = file_name[:-5] + "_playoff.json"
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
            file_name = file_name[:-5] + "_poules.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(pools, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/save/{file_name}", "w") as file:
                json.dump(pools, file, ensure_ascii=False)
            logger.info("Pools renewed")
        elif sport_config["Type"] == "Series":
            series = generate_series(new_teams, sport_config)
            file_name = file_name[:-5] + "_series.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
            with open(f"{data_dir}/teams/save/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
            logger.info("Series renewed")
        adapt_bet_file(data_dir, sport)
        for player in players_list():
            generate_event_list(player, data_dir)
        generate_can_be_added_list(sport, data_dir)
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
                    response.headers["Content-length"] = len(username)
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

    return app
