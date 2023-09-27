from enum import Enum

TEAM_NAMES = [
    "Kleinmazama",
    "Wapiti",
    "Karibu",
    "Pudu",
    "Elch",
    "Wasserreh",
    "Leierhirsch",
    "Barasingha",
    "Northern Pudú",
    "Southern Pudú",
    "Gray Brocket",
    "White-Tailed Deer",
    "Chital",
    "Chinese Muntjac",
    "Pygmy brocket",
    "Water Deer",
    "Brazilian Brocket",
    "Tufted Deer",
    "Siberian roe deer",
    "Dwarf brocket",
    "Mule deer",
    "Fallow deer",
    "Javan rusa",
    "Sambar deer",
    "Reindeer",
    "Moose",
    "Sangai",
    "Indian hog deer",
]


class Experience(Enum):
    NOOB = 0.01
    BEGINNER = 0.05
    INTERMEDIATE = 0.1
    ADVANCED = 0.2
    PRO = 0.3

    @staticmethod
    def from_str(s):
        if s == "noob":
            return Experience.NOOB
        elif s == "beginner":
            return Experience.BEGINNER
        elif s == "intermediate":
            return Experience.INTERMEDIATE
        elif s == "advanced":
            return Experience.ADVANCED
        elif s == "pro":
            return Experience.PRO
        else:
            raise NotImplementedError


#### Helpers ####


def _generate_ctf_team(id):
    new_team = {
        "id": id,
        "name": TEAM_NAMES[id - 1],
        "teamSubnet": "::ffff:<placeholder>",
        "address": "<placeholder>",
    }
    return new_team


def _generate_setup_team(id, experience, config):
    new_team = {
        TEAM_NAMES[id - 1]: {
            "id": id,
            "name": TEAM_NAMES[id - 1],
            "teamSubnet": "::ffff:<placeholder>",
            "address": "<placeholder>",
            "experience": experience,
            "exploiting": {
                service: "<placeholder>" for service in config["settings"]["services"]
            },
            "patched": {
                service: "<placeholder>" for service in config["settings"]["services"]
            },
        }
    }
    return new_team


#### End Helpers ####


class TeamGenerator:
    def __init__(self, config):
        self.config = config
        NOOB = (0.2, Experience.NOOB)
        BEGINNER = (0.2, Experience.BEGINNER)
        INTERMEDIATE = (0.3, Experience.INTERMEDIATE)
        ADVANCED = (0.2, Experience.ADVANCED)
        PRO = (0.1, Experience.PRO)
        self.team_distribution = {
            e: int(p * self.config["settings"]["teams"])
            for p, e in [
                NOOB,
                BEGINNER,
                INTERMEDIATE,
                ADVANCED,
                PRO,
            ]
        }
        while sum(self.team_distribution.values()) < self.config["settings"]["teams"]:
            self.team_distribution[Experience.NOOB] += 1
        while sum(self.team_distribution.values()) > self.config["settings"]["teams"]:
            self.team_distribution[Experience.NOOB] -= 1

    def generate(self):
        ctf_json_teams = []
        setup_teams = dict()
        team_id_total = 0

        for experience, teams in self.team_distribution.items():
            for team_id in range(1, teams + 1):
                ctf_json_teams.append(_generate_ctf_team(team_id_total + team_id))
                setup_teams.update(
                    _generate_setup_team(
                        team_id_total + team_id, experience, self.config
                    )
                )
            team_id_total += teams

        return ctf_json_teams, setup_teams
