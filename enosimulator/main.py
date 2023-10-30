import argparse
import asyncio
import os
import sys
from threading import Thread

from container_single import Container
from dotenv import load_dotenv


def get_args() -> argparse.Namespace:
    dir_path = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")

    parser = argparse.ArgumentParser(
        prog="enosimulator",
        description="Simulating an A/D CTF competition",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="A path to the config file containing service info and simulation setup info",
        default=os.environ.get(
            "ENOSIMULATOR_CONFIG", f"{dir_path}/../config/config.json"
        ),
    )
    parser.add_argument(
        "-s",
        "--secrets",
        help="A path to the secrets file containing ssh key paths and login credentials for cloud providers",
        default=os.environ.get(
            "ENOSIMULATOR_SECRETS", f"{dir_path}/../config/secrets.json"
        ),
    )
    parser.add_argument(
        "-D",
        "--destroy",
        action="store_true",
        help="Explicitly destroy the setup including all infrastructure in case of an unexpected error",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display additional statistics in each round",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Display additional information useful for debugging",
    )

    args = parser.parse_args()

    if not args.config:
        parser.print_usage()
        raise Exception(
            "Please supply the path to a config file or set the ENOSIMULATOR_CONFIG environment variable"
        )
    if not args.secrets:
        parser.print_usage()
        raise Exception(
            "Please supply the path to a secrets file or set the ENOSIMULATOR_SECRETS environment variable"
        )

    return args


async def main() -> None:
    load_dotenv()
    sys.path.append("..")
    sys.path.append("../..")
    args = get_args()

    container = Container()
    container.config.config.from_json(args.config)
    container.config.secrets.from_json(args.secrets)
    container.config.verbose.from_value(args.verbose)
    container.config.debug.from_value(args.debug)

    # Console().print(container.config())

    setup = container.setup()
    simulation = container.simulation()
    app = container.flask_app()

    if args.destroy:
        setup.destroy()
        return

    try:
        await setup.build()

        flask_thread = Thread(target=app.run)
        flask_thread.daemon = True
        flask_thread.start()

        await simulation.run()

        setup.destroy()

    except asyncio.exceptions.CancelledError:
        setup.destroy()


if __name__ == "__main__":
    asyncio.run(main())
