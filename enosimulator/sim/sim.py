import random
from time import sleep

from colorama import Fore
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


def _adjust_team(setup, team_name, variant, service, flagstore):
    if (
        variant == "exploiting"
        and not setup.teams[team_name].exploiting[service][flagstore]
    ):
        setup.teams[team_name].exploiting[service][flagstore] = True
        info_text = "started exploiting"
    elif (
        variant == "patched" and not setup.teams[team_name].patched[service][flagstore]
    ):
        setup.teams[team_name].patched[service][flagstore] = True
        info_text = "patched"
    print(Fore.GREEN + f"\n[+] Team {team_name} {info_text} {service}: {flagstore}\n")


#### End Helpers ####


class Simulation:
    def __init__(self, setup, orchestrator):
        self.setup = setup
        self.orchestrator = orchestrator

    @classmethod
    async def new(cls, setup):
        orchestrator = Orchestrator(setup)
        await orchestrator.update_teams()
        return cls(setup, orchestrator)

    def run(self):
        for round_id in range(self.setup.config["settings"]["duration-in-minutes"]):
            print(
                Fore.BLUE + f"\n==================ROUND {round_id}==================\n"
            )

            # Go through all teams and perform the random test
            for team_name, team in self.setup.teams.items():
                if _random_test(team):
                    variant, service, flagstore = _exploit_or_patch(team)
                    _adjust_team(self.setup, team_name, variant, service, flagstore)

            # TODO:
            # - it may be a good idea to do this concurrently for each team
            # - for this i could use the threading library and spawn a thread for each team
            # Instruct orchestrator to send out exploit requests

            sleep(60)
