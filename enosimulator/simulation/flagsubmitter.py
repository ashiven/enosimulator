from typing import List

import paramiko
from rich.console import Console
from setup.types import Config, IpAddresses, Secrets, SetupVariant


class FlagSubmitter:
    def __init__(
        self,
        ip_addresses: IpAddresses,
        config: Config,
        secrets: Secrets,
        verbose: bool = False,
        debug: bool = False,
    ):
        self.config = config
        self.secrets = secrets
        self.ip_addresses = ip_addresses
        self.verbose = verbose
        self.debug = debug
        self.usernames = {
            SetupVariant.AZURE: "groot",
            SetupVariant.HETZNER: "root",
            SetupVariant.LOCAL: "root",
        }
        self.console = Console()

    def submit_flags(self, team_address: str, flags: List[str]):
        SUBMISSION_ENDPOINT_PORT = 1337
        flag_str = "\n".join(flags) + "\n"

        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            vm_name, team_address = self._private_to_public_ip(team_address)
            client.connect(
                hostname=team_address,
                username=self.usernames[
                    SetupVariant.from_str(self.config.setup.location)
                ],
                pkey=paramiko.RSAKey.from_private_key_file(
                    self.secrets.vm_secrets.ssh_private_key_path
                ),
            )
            transport = client.get_transport()
            with transport.open_channel(
                "direct-tcpip",
                (
                    self.ip_addresses.private_ip_addresses["engine"],
                    SUBMISSION_ENDPOINT_PORT,
                ),
                ("localhost", 0),
            ) as channel:
                channel.send(flag_str.encode())
                if self.debug:
                    self.console.log(f"[bold blue]Submitted {flag_str}for {vm_name}\n")

    def _private_to_public_ip(self, team_address: str):
        for name, ip_address in self.ip_addresses.private_ip_addresses.items():
            if ip_address == team_address:
                return name, self.ip_addresses.public_ip_addresses[name]
