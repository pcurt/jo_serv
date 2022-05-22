# Standard lib imports
import hashlib
import json
import logging
import os
import re
import time

import mariadb  # type: ignore
import requests  # type: ignore
from flask import Flask, Response, request  # type: ignore


def create_server() -> Flask:
    """Create the server

    Returns:
        Flask: The server
    """
    logger = logging.getLogger(__name__)
    logger.info("Create the server")
    app = Flask(__name__)

    try:
        conn = mariadb.connect(user="root", database="JO")
        cur = conn.cursor()
        conn.autocommit = True
    except mariadb.Error as e:
        logger.error(f"Error connecting to MariaDB Platform: {e}")

    @app.route("/", methods=["GET", "POST"])
    def home() -> Response:
        """Main page for server

        Returns:
            Response: Welcome message
        """
        return Response(response="This is the JO server", status=200)

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

        cur.execute("SELECT * from users")
        for (id, user, pwd, autho, date) in cur:
            logger.debug(f"{id} {user} {pwd} {autho} {date}")
            if rcv_user == user:
                if rcv_password == pwd:
                    logger.info(f"Receive correct password for {user}")
                    return Response(response="Logged IN ", status=200)
                else:
                    logger.info(f"Receive invalid password for {user}")

        return Response(response="Wrong password ", status=403)

    @app.route("/chat/<name>", methods=["GET", "POST"])
    def chat(name: str) -> Response:
        """Chat endpoints

        Returns:
            Response: The chat file content
        """
        if request.method == "GET":
            logger.info(f"Get on /chat/{name}")
            path = "chat/" + name
            with open(path, "rb") as file:
                return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint chat", status=404)

    @app.route("/teams/<name>", methods=["GET", "POST"])
    def teams(name: str) -> Response:
        """Teams endpoints

        Returns:
            Response: The chat file content
        """
        if request.method == "GET":
            logger.info(f"Get on /teams/{name}")
            path = "teams/" + name
            with open(path, "rb") as file:
                return Response(response=file.read(), status=200)

        return Response(response="Error on endpoint teams", status=404)

    @app.route("/pushtoken", methods=["POST"])
    def pushtoken() -> Response:
        decode_data = request.data.decode("utf-8")
        json_data = json.loads(decode_data)
        json_data["token"] = "ExponentPushToken[Nf2CeYB3BZgOUjc083HxOz]"
        logger.info(f"Data received : {decode_data}")

        if json_data.get("token"):
            if not os.path.exists("tokens.txt"):
                open("tokens.txt", "w")
            if (
                json_data.get("token") not in open(data_dir + "/tokens.txt", "r").read()
            ):  # just to be sure we don't write again the same
                if json_data.get("username"):
                    open(data_dir + "/tokens.txt", "a").write(
                        json_data.get("token") + ":" + json_data.get("username") + "\n"
                    )
                else:
                    open(data_dir + "/tokens.txt", "a").write(json_data.get("token") + ":\n")
            elif json_data.get("username") != "":
                lines = open(data_dir +"/tokens.txt", "r").readlines()
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

        if os.path.exists("lasttimecluedo"):
            last_time = float(open("lasttimecluedo", "r").read())
        else:
            last_time = time.time() - 16 * 60
        if time.time() > (last_time + 15 * 60):  # filter 15 mins
            logger.info("cluedotime")
            tokens = open("tokens.txt", "r").readlines()
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
                        open(data_dir + "/tokens.txt", "w").write(full_txt.replace(token, ""))
            open(data_dir + "/lasttimecluedo", "w").write(str(time.time()))
        else:
            logger.info("ignore as it's less than 15 mins since last")
        return Response(response="fdp", status=200)

    return app
