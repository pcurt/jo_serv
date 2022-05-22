"""Console script for jo_serv."""

# Standard lib imports
import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

# Third-party lib imports
import click

# Local package imports
from jo_serv.server.server import create_server


# Define this function as a the main command entrypoint
@click.group()
# Create an argument that expects a path to a valid file
@click.option(
    "--log-config",
    help="Path to the log config file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        writable=False,
        readable=True,
        resolve_path=True,
    ),
)
# Display the help if no option is provided
@click.help_option()
def main(
    log_config: Optional[str],
) -> None:
    """Console script for jo_serv."""
    if log_config is not None:
        logging.config.fileConfig(log_config)
    else:
        # Default to some basic config
        log_config = f"{Path(__file__).parent}/log.cfg"
        logging.config.fileConfig(log_config)
        tmp_logger = logging.getLogger(__name__)
        tmp_logger.warning("No log config provided, using default configuration")
    logger = logging.getLogger(__name__)
    logger.info("Logger initialized")


@main.command()
def srv() -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start server")
    app = create_server()
    app.run(host="0.0.0.0", port=7070, debug=True, use_reloader=False)  # nosec
    logger.info("Server is running")


@main.command()
def tools() -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start tools")


if __name__ == "__main__":
    sys.exit(main())
