# Standard lib imports
import datetime
import hashlib
import json
import logging
import os
import re
import sys
import time

import mariadb  # type: ignore
import requests  # type: ignore
from flask import Flask, Response, request  # type: ignore

from jo_serv.tools.tools import (
    adapt_bet_file,
    generate_pizza_results,
    generate_pools,
    generate_series,
    generate_table,
    get_sport_config,
    send_notif,
    team_to_next_step,
    trigger_tas_dhommes,
    update_bet_file,
    update_global_results,
    update_list,
    update_playoff_match,
    update_poules_match,
    user_is_authorized,
)


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
            sys.exit(-1)

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
            logger.info("cluedotime")
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
                        full_txt = open("tokens.txt", "r").read()
                        open(data_dir + "/tokens.txt", "w").write(
                            full_txt.replace(token, "")
                        )
            open(data_dir + "/lasttimecluedo", "w").write(str(time.time()))
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

        if sport == "Pizza":
            logger.info("Push for pizza")
            trigger_tas_dhommes(match, username, data_dir)
            update_list(f"{sport}/{username}", match, data_dir)
            generate_pizza_results(data_dir)
        else:
            if user_is_authorized(username, sport, data_dir):
                logger.info("User is authorized")
                logger.info(f"Type is {type}")
                if type == "playoff":
                    match_id = int(match["uniqueId"])
                    logger.info(
                        f"update_playoff {sport}, {match_id}, {match}, {data_dir}"
                    )
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
            logger.info("Pools renewed")
        elif sport_config["Type"] == "Series":
            series = generate_series(new_teams, sport_config)
            file_name = file_name[:-5] + "_series.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
            logger.info("Series renewed")
        adapt_bet_file(data_dir, sport)
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

    return app
