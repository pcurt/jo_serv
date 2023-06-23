"""Console script for jo_serv."""

# Standard lib imports
import logging
import logging.config
import sys
import threading
from pathlib import Path
from typing import Optional

# Third-party lib imports
import click
from waitress import serve  # type: ignore

# Local package imports
from jo_serv.server.server import create_server
from jo_serv.tools.canva import canva_png_creator
from jo_serv.tools.event import event_handler
from jo_serv.tools.shifumi import shifumi_process
from jo_serv.tools.tools import (
    create_empty_bet_files,
    generate_killer,
    increase_canva_size,
    update_global_bets_results,
    update_global_results,
)


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


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@main.command()
def srv(
    data_dir: str,
) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start server")
    logger.info(f"{data_dir}")

    event = threading.Thread(target=event_handler, args=(data_dir,))
    event.start()
    canva = threading.Thread(target=canva_png_creator, args=(data_dir,))
    canva.start()
    logger.info("Starting shifumi")
    shifumi = threading.Thread(target=shifumi_process, args=(data_dir,))
    shifumi.start()

    logger.info("Shifumi started")
    app = create_server(data_dir=data_dir)
    serve(app, port=8000)
    logger.info("Server is stopped")


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@main.command()
def generate_results(
    data_dir: str,
) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start generate_results")
    update_global_bets_results(data_dir=data_dir)


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@main.command()
def generate_bets(
    data_dir: str,
) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start generate_bets")
    create_empty_bet_files(data_dir=data_dir)


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@main.command()
def global_results(
    data_dir: str,
) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start update_global_results")
    update_global_results(data_dir=data_dir)


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@click.option("-x", help="tile_x", default=0, type=int)
@click.option("-y", help="tile_y", default=0, type=int)
@main.command()
def enlarge(data_dir: str, x: int = 0, y: int = 0) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start increase_canva_size")
    increase_canva_size(data_dir=data_dir, tile_x=x, tile_y=y)


@click.option(
    "--data-dir",
    help="Path to the data dir",
    default="./",
    type=click.Path(
        exists=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
)
@main.command()
def gen_killer(
    data_dir: str,
) -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start generate_killer")
    generate_killer(data_dir=data_dir)


if __name__ == "__main__":
    sys.exit(main())
