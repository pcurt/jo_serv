# Standard lib imports
import logging

from flask import Flask, Response, request  # type: ignore


def create_server() -> Flask:
    """Create the server

    Returns:
        Flask: The server
    """
    app = Flask(__name__)
    logger = logging.getLogger(__name__)
    logger.info("Initialization success")

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
        logger.info("Login")
        # TODO
        if request.method == "GET":
            logger.info("c'est Open bar")

        return Response(response="Logged IN ", status=200)

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
