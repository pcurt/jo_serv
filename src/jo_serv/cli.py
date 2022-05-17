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
from jo_serv.example_module import ExampleClass


# Define this function as a the main command entrypoint
@click.command()
# Create an argument that expects an integer, and has a default value
@click.option(
    "-n",
    "--iterations",
    help="Number of times to display the sample text",
    type=int,
    default=1,
)
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
    iterations: int,
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
    instance = ExampleClass()
    for i in range(iterations):
        logger.info(f"Iteration number {i}: {instance.add(i, i)}")


if __name__ == "__main__":
    sys.exit(main())
