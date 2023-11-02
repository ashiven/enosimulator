import os
from unittest.mock import AsyncMock, Mock

import pytest

from enosimulator.types_ import Experience, Service, Team


def test_team_generator_basic_stress_test(setup_container):
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {"settings": {"teams": 50, "simulation-type": "basic-stress-test"}}
    )
    team_generator = setup_container.team_generator()
    assert all([exp.name == "HAXXOR" for exp in team_generator.team_distribution])

    ctf_json_teams, setup_teams = team_generator.generate()
    assert len(ctf_json_teams) == 1
    assert len(ctf_json_teams) == len(setup_teams)


def test_team_generator_stress_test(setup_container):
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {"settings": {"teams": 3, "simulation-type": "stress-test"}}
    )
    team_generator = setup_container.team_generator()
    assert all([exp.name == "HAXXOR" for exp in team_generator.team_distribution])

    ctf_json_teams, setup_teams = team_generator.generate()
    assert len(ctf_json_teams) == 3
    assert len(ctf_json_teams) == len(setup_teams)


def test_team_generator_realistic(setup_container, test_setup_dir):
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {"settings": {"teams": 15, "simulation-type": "realistic"}}
    )
    team_generator = setup_container.team_generator()
    assert all(
        [
            team_exp in [exp.name for exp in team_generator.team_distribution]
            for team_exp in ["NOOB", "BEGINNER", "INTERMEDIATE", "ADVANCED", "PRO"]
        ]
    )
    ctf_json_teams, setup_teams = team_generator.generate()
    assert len(ctf_json_teams) == 15
    assert len(ctf_json_teams) == len(setup_teams)


@pytest.mark.asyncio
async def test_setup_helper_azure(mock_fs, setup_container, test_setup_dir):
    mock_fs.add_real_directory(test_setup_dir, read_only=False)
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {
            "setup": {
                "location": "azure",
            },
            "settings": {
                "teams": 3,
                "simulation-type": "realistic",
            },
        }
    )
    setup_helper = setup_container.setup_helper()
    list(setup_helper.helpers.values())[0].setup_path = test_setup_dir + "/azure"
    await setup_helper.convert_templates()

    assert os.path.exists(test_setup_dir + "/azure/data/checker.sh")
    assert os.path.exists(test_setup_dir + "/azure/data/docker-compose.yml")
    assert os.path.exists(test_setup_dir + "/azure/data/engine.sh")
    assert os.path.exists(test_setup_dir + "/azure/data/vulnbox.sh")
    assert os.path.exists(test_setup_dir + "/azure/build.sh")
    assert os.path.exists(test_setup_dir + "/azure/deploy.sh")
    assert os.path.exists(test_setup_dir + "/azure/main.tf")
    assert os.path.exists(test_setup_dir + "/azure/outputs.tf")
    assert os.path.exists(test_setup_dir + "/azure/variables.tf")
    assert os.path.exists(test_setup_dir + "/azure/versions.tf")

    mock_fs.create_file(
        test_setup_dir + "/azure/logs/ip_addresses.log",
        contents="private_ip_addresses = {\n"
        + '  "vulnbox1" = "10.1.0.1"\n'
        + '  "checker" = "10.1.0.2"\n'
        + '  "engine" = "10.1.0.3"\n}\n'
        + 'vulnbox1 = "123.23.23.12"\n'
        + 'checker = "123.32.32.21"\n'
        + 'engine = "254.32.32.21"\n',
    )
    public_ips, private_ips = await setup_helper.get_ip_addresses()

    assert public_ips == {
        "vulnbox1": "123.23.23.12",
        "checker": "123.32.32.21",
        "engine": "254.32.32.21",
    }

    assert private_ips == {
        "vulnbox1": "10.1.0.1",
        "checker": "10.1.0.2",
        "engine": "10.1.0.3",
    }


@pytest.mark.asyncio
async def test_setup_helper_hetzner(mock_fs, setup_container, test_setup_dir):
    mock_fs.add_real_directory(test_setup_dir, read_only=False)
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {
            "setup": {
                "location": "hetzner",
            },
            "settings": {
                "teams": 3,
                "simulation-type": "stress-test",
            },
        }
    )
    setup_helper = setup_container.setup_helper()
    list(setup_helper.helpers.values())[1].setup_path = test_setup_dir + "/hetzner"
    await setup_helper.convert_templates()

    assert os.path.exists(test_setup_dir + "/hetzner/data/checker.sh")
    assert os.path.exists(test_setup_dir + "/hetzner/data/docker-compose.yml")
    assert os.path.exists(test_setup_dir + "/hetzner/data/engine.sh")
    assert os.path.exists(test_setup_dir + "/hetzner/data/vulnbox.sh")
    assert os.path.exists(test_setup_dir + "/hetzner/build.sh")
    assert os.path.exists(test_setup_dir + "/hetzner/deploy.sh")
    assert os.path.exists(test_setup_dir + "/hetzner/main.tf")
    assert os.path.exists(test_setup_dir + "/hetzner/outputs.tf")
    assert os.path.exists(test_setup_dir + "/hetzner/variables.tf")
    assert os.path.exists(test_setup_dir + "/hetzner/versions.tf")

    mock_fs.create_file(
        test_setup_dir + "/hetzner/logs/ip_addresses.log",
        contents="vulnbox_public_ips = {\n"
        + '  "vulnbox1" = "234.123.12.32"\n'
        + '  "vulnbox2" = "234.231.12.32"\n'
        + '  "vulnbox3" = "234.123.32.12"\n}\n'
        + 'checker = "123.32.32.21"\n'
        + 'engine = "123.32.23.21"\n',
    )
    public_ips, private_ips = await setup_helper.get_ip_addresses()

    assert public_ips == {
        "vulnbox1": "234.123.12.32",
        "vulnbox2": "234.231.12.32",
        "vulnbox3": "234.123.32.12",
        "checker": "123.32.32.21",
        "engine": "123.32.23.21",
    }

    assert private_ips == {
        "vulnbox1": "10.1.1.1",
        "vulnbox2": "10.1.2.1",
        "vulnbox3": "10.1.3.1",
        "checker": "10.1.4.1",
        "engine": "10.1.5.1",
    }


# TODO: - implement
@pytest.mark.asyncio
async def test_setup_helper_local(mock_fs, setup_container, test_setup_dir):
    pass


@pytest.mark.asyncio
async def test_setup_configure(mock_fs, setup_container, test_setup_dir):
    mock_fs.add_real_directory(test_setup_dir, read_only=False)
    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {
            "setup": {
                "location": "hetzner",
            },
            "settings": {
                "teams": 1,
                "simulation-type": "realistic",
            },
        }
    )
    setup = setup_container.setup()
    setup.setup_path = test_setup_dir + "/hetzner"
    setup.setup_helper.generate_teams = Mock()
    ctf_teams = [
        {
            "id": 1,
            "name": "TestTeam",
            "teamSubnet": "::ffff:<placeholder>",
            "address": "<placeholder>",
        }
    ]

    setup_teams = {
        "TestTeam": Team(
            id=1,
            name="TestTeam",
            team_subnet="::ffff:<placeholder>",
            address="<placeholder>",
            experience=Experience.NOOB,
            exploiting=dict(),
            patched=dict(),
            points=0.0,
            gain=0.0,
        )
    }
    setup.setup_helper.generate_teams.return_value = (ctf_teams, setup_teams)
    setup.setup_helper.convert_templates = AsyncMock()
    await setup.configure()

    assert os.path.exists(test_setup_dir + "/hetzner/config/services.txt")
    assert os.path.exists(test_setup_dir + "/hetzner/config/ctf.json")

    assert (
        "enowars7-service-CVExchange"
        in open(test_setup_dir + "/hetzner/config/services.txt").read()
    )
    assert (
        "enowars7-service-bollwerk"
        in open(test_setup_dir + "/hetzner/config/services.txt").read()
    )


@pytest.mark.asyncio
async def test_setup_build(mock_fs, setup_container, test_setup_dir):
    mock_fs.add_real_directory(test_setup_dir, read_only=False)
    ctf_json_contents = """{
    "title": "ctf-sim",
    "flagValidityInRounds": 2,
    "checkedRoundsPerRound": 3,
    "roundLengthInSeconds": 60,
    "dnsSuffix": "eno.host",
    "teamSubnetBytesLength": 15,
    "flagSigningKey": "ir7PRm0SzqzA0lmFyBfUv68E6Yb7cjbJDp6dummqwr0Od70Sar7P27HVY6oc8PuW",
    "teams": [
        {
            "id": 1,
            "name": "TestTeam",
            "teamSubnet": "::ffff:<placeholder>",
            "address": "<placeholder>"
        }
    ],
    "services": [
        {
            "id": 1,
            "name": "enowars7-service-CVExchange",
            "flagsPerRoundMultiplier": 1,
            "noisesPerRoundMultiplier": 1,
            "havocsPerRoundMultiplier": 1,
            "weightFactor": 1,
            "checkers": [
                "7331"
            ]
        }
    ],
    "flag_validity_in_rounds": 2,
    "checked_rounds_per_round": 3,
    "round_length_in_seconds": 60
}"""
    mock_fs.create_file(
        test_setup_dir + "/hetzner/config/ctf.json",
        contents=ctf_json_contents,
    )

    setup_container.reset_singletons()
    setup_container.configuration.config.from_dict(
        {
            "setup": {
                "location": "hetzner",
            },
            "settings": {
                "teams": 1,
                "simulation-type": "realistic",
            },
        }
    )
    setup = setup_container.setup()
    setup.setup_path = test_setup_dir + "/hetzner"
    setup._existing_infra = Mock()
    setup._existing_infra.return_value = True

    teams = {
        "TestTeam": Team(
            id=1,
            name="TestTeam",
            team_subnet="::ffff:<placeholder>",
            address="<placeholder>",
            experience=Experience.NOOB,
            exploiting=dict(),
            patched=dict(),
            points=0.0,
            gain=0.0,
        )
    }
    services = {
        "enowars7-service-CVExchange": Service(
            id=1,
            name="enowa7-service-CVExchange",
            flags_per_round_multiplier=1,
            noises_per_round_multiplier=1,
            havocs_per_round_multiplier=1,
            weight_factor=1,
            checkers=["7331"],
        )
    }
    setup.teams = teams
    setup.services = services

    setup.setup_helper.get_ip_addresses = AsyncMock()
    public_ips = {
        "vulnbox1": "234.123.12.32",
        "checker": "123.32.32.21",
        "engine": "123.32.23.21",
    }
    private_ips = {
        "vulnbox1": "10.1.1.1",
        "checker": "10.1.4.1",
        "engine": "10.1.5.1",
    }
    setup.setup_helper.get_ip_addresses.return_value = (public_ips, private_ips)
    setup.info = Mock()
    setup.info.return_value = None
    await setup.build_infra()

    assert setup.teams["TestTeam"].address == "10.1.1.1"
    assert setup.services["enowars7-service-CVExchange"].checkers == [
        "http://123.32.32.21:7331"
    ]
    assert open(test_setup_dir + "/hetzner/config/ctf.json").read() != ctf_json_contents
