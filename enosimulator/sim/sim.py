import asyncio
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.table import Table
from sim.orchestrator import Orchestrator

#### Helpers ####


def _random_test(team):
    probability = team.experience.value
    random_value = random.random()
    return random_value < probability


def _exploit_or_patch(team):
    random_variant = random.choice(["exploiting", "patched"])
    if random_variant == "exploiting":
        random_service = random.choice(list(team.exploiting))
        random_flagstore = random.choice(list(team.exploiting[random_service]))
    else:
        random_service = random.choice(list(team.patched))
        random_flagstore = random.choice(list(team.patched[random_service]))

    return random_variant, random_service, random_flagstore


#### End Helpers ####


class Simulation:
    def __init__(self, setup, orchestrator):
        self.setup = setup
        self.orchestrator = orchestrator
        self.round_id = 0
        self.console = Console()

    @classmethod
    async def new(cls, setup):
        orchestrator = Orchestrator(setup)
        await orchestrator.update_team_info()
        return cls(setup, orchestrator)

    async def run(self):
        for _ in range(self.setup.config["settings"]["duration-in-minutes"]):
            self.round_id = await self.orchestrator.get_round_info()
            self.round_info()

            # Go through all teams and perform the random test
            for team_name, team in self.setup.teams.items():
                if _random_test(team):
                    variant, service, flagstore = _exploit_or_patch(team)
                    self._update_team(team_name, variant, service, flagstore)

            # Instruct orchestrator to send out exploit requests
            team_flags = dict()
            async with asyncio.TaskGroup() as task_group:
                for team in self.setup.teams.values():
                    flags = await task_group.create_task(
                        self.orchestrator.exploit(
                            self.round_id, team, self.setup.teams.values()
                        )
                    )
                    team_flags[team.name] = (team.address, flags)

            # Instruct orchestrator to submit flags
            with ThreadPoolExecutor(max_workers=20) as executor:
                for team_address, flags in team_flags.values():
                    if flags:
                        executor.submit(
                            self.orchestrator.submit_flags, team_address, flags
                        )

            await asyncio.sleep(60)

    def round_info(self):
        os.system("cls" if sys.platform == "win32" else "clear")
        self.console.print("\n")
        self.console.log(f"[bold blue]Round {self.round_id} info:\n")

        for team in self.setup.teams.values():
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
            self.console.print(table)

    def _update_team(self, team_name, variant, service, flagstore):
        if variant == "exploiting":
            self.setup.teams[team_name].exploiting[service][flagstore] = True
            info_text = "started exploiting"
        elif variant == "patched":
            self.setup.teams[team_name].patched[service][flagstore] = True
            info_text = "patched"
        self.console.print(
            f"[bold yellow][!] Team {team_name} {info_text} {service}: {flagstore}"
        )
