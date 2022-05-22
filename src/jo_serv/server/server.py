# Standard lib imports
import hashlib
import json
import logging

import mariadb  # type: ignore
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

    return app
