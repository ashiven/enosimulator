import asyncio
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from time import time
from typing import Dict, List, Tuple

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from types_ import OrchestratorType, SetupType, Team

from .orchestrator import Orchestrator
from .util import async_lock


class Simulation:
    def __init__(
        self,
        setup: SetupType,
        orchestrator: OrchestratorType,
        locks: Dict,
        verbose: bool,
        debug: bool,
    ):
        self.setup = setup
        self.locks = locks
        self.orchestrator = orchestrator
        self.verbose = verbose
        self.debug = debug
        self.console = Console()
        self.round_id = 0
        self.round_start = 0
        self.total_rounds = setup.config.settings.duration_in_minutes * (
            60 // setup.config.ctf_json.round_length_in_seconds
        )
        self.remaining_rounds = self.total_rounds
        self.round_length = setup.config.ctf_json.round_length_in_seconds

    @classmethod
    async def new(
        cls, setup: SetupType, locks: Dict, verbose: bool = False, debug: bool = False
    ):
        orchestrator = Orchestrator(setup, locks, verbose, debug)
        await orchestrator.update_team_info()
        return cls(setup, orchestrator, locks, verbose, debug)

    async def run(self) -> None:
        await self._scoreboard_available()

        for round_ in range(self.total_rounds):
            async with async_lock(self.locks["round_info"]):
                self.round_start = time()
                self.remaining_rounds = self.total_rounds - round_
                self.round_id = await self.orchestrator.get_round_info()

            info_messages = await self._update_exploiting_and_patched()
            self.info(info_messages)

            self.orchestrator.parse_scoreboard()

            # Send out exploit tasks while collecting system analytics
            exploit_task = asyncio.get_event_loop().create_task(
                self._exploit_all_teams()
            )
            container_panels, system_panels = self._system_analytics()

            # Submit collected flags
            flags = await exploit_task
            self._submit_all_flags(flags)

            # Print system analytics and store them in the database
            self._print_system_analytics(container_panels, system_panels)
            await self.orchestrator.collect_system_analytics()

            round_end = time()
            round_duration = round_end - self.round_start
            if round_duration < self.round_length:
                await asyncio.sleep(self.round_length - round_duration)

    def info(self, info_messages: List[str]) -> None:
        os.system("cls" if sys.platform == "win32" else "clear")
        self.console.print("\n")
        self.console.log(
            f"[bold blue]Round {self.round_id} ({self.remaining_rounds} rounds remaining):\n"
        )

        if self.verbose:
            self.setup.info()
            self.console.print("\n\n[bold red]Attack info:")
            self.console.print(self.orchestrator.attack_info)

        self.console.print("\n")

        with self.locks["team"]:
            self._team_info(self.setup.teams.values())

        self.console.print("\n")
        if self.verbose:
            for info_message in info_messages:
                self.console.print(info_message)
            self.console.print("\n")

    async def _scoreboard_available(self) -> None:
        with self.console.status(
            "[bold green]Waiting for scoreboard to become available ..."
        ):
            while not self.orchestrator.attack_info:
                await self.orchestrator.get_round_info()
                await asyncio.sleep(2)

    def _team_info(self, teams: List[Team]) -> None:
        tables = []
        for team in teams:
            table = Table(
                title=f"Team {team.name} - {str(team.experience)}",
                title_style="bold magenta",
                title_justify="left",
            )
            table.add_column("Exploiting", justify="center", style="magenta")
            table.add_column("Patched", justify="center", style="cyan")

            exploiting = []
            for service, flagstores in team.exploiting.items():
                for flagstore, do_exploit in flagstores.items():
                    if do_exploit:
                        exploiting.append(service + "-" + flagstore)

            patched = []
            for service, flagstores in team.patched.items():
                for flagstore, do_patch in flagstores.items():
                    if do_patch:
                        patched.append(service + "-" + flagstore)
            max_len = max(len(exploiting), len(patched))
            info_list = [
                (
                    exploiting[i] if i < len(exploiting) else None,
                    patched[i] if i < len(patched) else None,
                )
                for i in range(max_len)
            ]

            for exploit_info, patch_info in info_list:
                table.add_row(exploit_info, patch_info)
            tables.append(table)
        self.console.print(Columns(tables))

    def _random_test(self, team: Team) -> bool:
        probability = team.experience.value[0]
        random_value = random.random()
        return random_value < probability

    def _exploit_or_patch(self, team: Team) -> Tuple[str, str, str]:
        try:
            random_variant = random.choice(["exploiting", "patched"])
            if random_variant == "exploiting":
                random_service = random.choice(list(team.exploiting))
                exploit_dict = team.exploiting[random_service]
                currently_not_exploiting = {
                    flagstore: exploiting
                    for flagstore, exploiting in exploit_dict.items()
                    if not exploiting
                }
                random_flagstore = random.choice(list(currently_not_exploiting))
            else:
                random_service = random.choice(list(team.patched))
                patched_dict = team.patched[random_service]
                currently_not_patched = {
                    flagstore: patched
                    for flagstore, patched in patched_dict.items()
                    if not patched
                }
                random_flagstore = random.choice(list(currently_not_patched))

            return random_variant, random_service, random_flagstore

        except IndexError:
            return None, None, None

    def _update_team(
        self, team_name: str, variant: str, service: str, flagstore: str
    ) -> str:
        if variant == "exploiting":
            self.setup.teams[team_name].exploiting[service][flagstore] = True
            info_text = "started exploiting"
        elif variant == "patched":
            self.setup.teams[team_name].patched[service][flagstore] = True
            info_text = "patched"
        else:
            return ""

        return f"[bold red][!] Team {team_name} {info_text} {service}-{flagstore}"

    async def _update_exploiting_and_patched(self) -> List[str]:
        info_messages = []
        if self.setup.config.settings.simulation_type == "realistic":
            async with async_lock(self.locks["team"]):
                for team_name, team in self.setup.teams.items():
                    if self._random_test(team):
                        variant, service, flagstore = self._exploit_or_patch(team)
                        info_message = self._update_team(
                            team_name, variant, service, flagstore
                        )
                        info_messages.append(info_message)

        return info_messages

    async def _exploit_all_teams(self) -> List:
        exploit_status = self.console.status("[bold green]Sending exploits ...")
        if not self.debug:
            exploit_status.start()

        team_flags = []
        for team in self.setup.teams.values():
            team_flags.append([team.address])

        async with asyncio.TaskGroup() as task_group:
            tasks = [
                task_group.create_task(
                    self.orchestrator.exploit(
                        self.round_id, team, self.setup.teams.values()
                    )
                )
                for team in self.setup.teams.values()
            ]

        for task_index, task in enumerate(tasks):
            team_flags[task_index].append(task.result())

        if not self.debug:
            exploit_status.stop()

        return team_flags

    def _system_analytics(self) -> Tuple[Dict[str, Panel], Dict[str, List[Panel]]]:
        container_panels = self.orchestrator.container_stats(
            self.setup.ips.public_ip_addresses
        )
        system_panels = self.orchestrator.system_stats(
            self.setup.ips.public_ip_addresses
        )

        return container_panels, system_panels

    def _submit_all_flags(self, team_flags: List) -> None:
        with ThreadPoolExecutor(
            max_workers=self.setup.config.settings.teams
        ) as executor:
            for team_address, flags in team_flags:
                if flags:
                    executor.submit(self.orchestrator.submit_flags, team_address, flags)

    def _print_system_analytics(self, container_panels, system_panels) -> None:
        if self.verbose:
            for name, container_stat_panel in container_panels.items():
                self.console.print(f"[bold red]Docker stats for {name}:")
                self.console.print(container_stat_panel)
                self.console.print("")

            for name, system_stat_panel in system_panels.items():
                self.console.print(f"[bold red]System stats for {name}:")
                self.console.print(Columns(system_stat_panel))
                self.console.print("")

            self.console.print("\n")
