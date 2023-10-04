import os
import re
from abc import ABC, abstractmethod

import aiofiles

from enosimulator.setup.teamgen import TeamGenerator
from enosimulator.setup.types import SetupVariant

####  Helpers ####


async def _copy_file(src, dst):
    if os.path.exists(src):
        async with aiofiles.open(src, "rb") as src_file:
            async with aiofiles.open(dst, "wb") as dst_file:
                content = await src_file.read()
                await dst_file.write(content)


async def _replace_line(path, line_number, new_line):
    async with aiofiles.open(path, "rb+") as file:
        lines = await file.readlines()
        lines[line_number] = new_line.replace("\\", "/").encode("utf-8")
        await file.seek(0)
        await file.writelines(lines)
        await file.truncate()


async def _insert_after(path, after, insert_lines):
    new_lines = []
    async with aiofiles.open(path, "rb") as file:
        lines = await file.readlines()
        for line in lines:
            new_lines.append(line)
            if line.startswith(after.encode("utf-8")):
                for insert_line in insert_lines:
                    new_lines.append(insert_line.encode("utf-8"))
    async with aiofiles.open(path, "wb") as file:
        await file.writelines(new_lines)


async def _append_lines(path, append_lines):
    async with aiofiles.open(path, "ab") as file:
        for line in append_lines:
            await file.write(line.encode("utf-8"))


async def _delete_lines(path, delete_lines):
    new_lines = []
    async with aiofiles.open(path, "rb") as file:
        lines = await file.readlines()
        for index, line in enumerate(lines):
            if index not in delete_lines:
                new_lines.append(line)
    async with aiofiles.open(path, "wb") as file:
        await file.writelines(new_lines)


#### End Helpers ####


class Helper(ABC):
    @abstractmethod
    async def convert_buildscript(self):
        pass

    @abstractmethod
    async def convert_deploy_script(self):
        pass

    @abstractmethod
    async def convert_tf_files(self):
        pass

    @abstractmethod
    async def convert_vm_scripts(self):
        pass

    @abstractmethod
    async def get_ip_addresses(self):
        pass


class AzureSetupHelper(Helper):
    def __init__(self, config, secrets):
        self.config = config
        self.secrets = secrets
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        self.setup_path = f"{dir_path}/../../test-setup/{config['setup']['location']}"
        self.use_vm_images = any(
            ref != "" for ref in self.config["setup"]["vm-image-references"].values()
        )

    async def convert_buildscript(self):
        # Copy build.sh template for configuration
        await _copy_file(
            f"{self.setup_path}/templates/build.sh",
            f"{self.setup_path}/build.sh",
        )

        # Configure setup_path, ssh_config_path and ssh_private_key_path
        ABSOLUTE_SETUP_PATH_LINE = 4
        SSH_CONFIG_PATH_LINE = 5
        SSH_PRIVATE_KEY_PATH_LINE = 6
        await _replace_line(
            f"{self.setup_path}/build.sh",
            ABSOLUTE_SETUP_PATH_LINE,
            f'setup_path="{os.path.abspath(self.setup_path)}"\n',
        )
        await _replace_line(
            f"{self.setup_path}/build.sh",
            SSH_CONFIG_PATH_LINE,
            f"ssh_config=\"{self.config['setup']['ssh-config-path']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/build.sh",
            SSH_PRIVATE_KEY_PATH_LINE,
            f"ssh_private_key_path=\"{self.secrets['vm-secrets']['ssh-private-key-path']}\"\n",
        )

        # Configure ip address parsing
        lines = []
        for vulnbox_id in range(1, self.config["settings"]["vulnboxes"] + 1):
            lines.append(
                f'vulnbox{vulnbox_id}_ip=$(grep -oP "vulnbox{vulnbox_id}\s*=\s*\K[^\s]+" ./logs/ip_addresses.log | sed \'s/"//g\')\n'
            )
        await _insert_after(f"{self.setup_path}/build.sh", "engine_ip=", lines)

        # Configure writing ssh config
        lines = []
        for vulnbox_id in range(1, self.config["settings"]["vulnboxes"] + 1):
            lines.append(
                f'echo -e "Host vulnbox{vulnbox_id}\\nUser groot\\nHostName ${{vulnbox{vulnbox_id}_ip}}\\nIdentityFile ${{ssh_private_key_path}}\\nStrictHostKeyChecking no\\nLocalForward 1337 ${{engine_private_ip}}:1337" >>${{ssh_config}}\n'
            )
        await _insert_after(
            f"{self.setup_path}/build.sh", 'echo -e "Host engine', lines
        )

    async def convert_deploy_script(self):
        # Copy deploy.sh template for configuration
        await _copy_file(
            f"{self.setup_path}/templates/deploy.sh",
            f"{self.setup_path}/deploy.sh",
        )

        # Configure setup_path, ssh_config_path
        ABSOLUTE_SETUP_PATH_LINE = 4
        SSH_CONFIG_PATH_LINE = 5
        await _replace_line(
            f"{self.setup_path}/deploy.sh",
            ABSOLUTE_SETUP_PATH_LINE,
            f'setup_path="{os.path.abspath(self.setup_path)}"\n',
        )
        await _replace_line(
            f"{self.setup_path}/deploy.sh",
            SSH_CONFIG_PATH_LINE,
            f"ssh_config=\"{self.config['setup']['ssh-config-path']}\"\n",
        )

        # Configure vulnbox deployments
        lines = []
        for vulnbox_id in range(1, self.config["settings"]["vulnboxes"] + 1):
            lines.append(
                f'\necho -e "\\n\\033[32m[+] Configuring vulnbox{vulnbox_id} ...\\033[0m"\n'
            )
            lines.append(
                f"retry scp -F ${{ssh_config}} ./data/vulnbox.sh vulnbox{vulnbox_id}:/home/groot/vulnbox.sh\n"
            )
            lines.append(
                f"retry scp -F ${{ssh_config}} ./config/services.txt vulnbox{vulnbox_id}:/home/groot/services.txt\n"
            )
            lines.append(
                f'retry ssh -F ${{ssh_config}} vulnbox{vulnbox_id} "chmod +x vulnbox.sh && ./vulnbox.sh" > ./logs/vulnbox{vulnbox_id}_config.log 2>&1 &\n'
            )
        await _insert_after(
            f"{self.setup_path}/deploy.sh", "retry ssh -F ${ssh_config} checker", lines
        )

    async def convert_tf_files(self):
        # Copy terraform file templates for configuration
        await _copy_file(
            f"{self.setup_path}/templates/versions.tf",
            f"{self.setup_path}/versions.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/main.tf",
            f"{self.setup_path}/main.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/variables.tf",
            f"{self.setup_path}/variables.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/outputs.tf",
            f"{self.setup_path}/outputs.tf",
        )

        # Add service principal credentials to versions.tf
        TF_SUBSCRIPTION_ID_LINE = 11
        TF_CLIENT_ID_LINE = 12
        TF_CLIENT_SECRET_LINE = 13
        TF_TENANT_ID_LINE = 14
        await _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_SUBSCRIPTION_ID_LINE,
            f"  subscription_id = \"{self.secrets['cloud-secrets']['azure-service-principal']['subscription-id']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_CLIENT_ID_LINE,
            f"  client_id       = \"{self.secrets['cloud-secrets']['azure-service-principal']['client-id']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_CLIENT_SECRET_LINE,
            f"  client_secret   = \"{self.secrets['cloud-secrets']['azure-service-principal']['client-secret']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_TENANT_ID_LINE,
            f"  tenant_id       = \"{self.secrets['cloud-secrets']['azure-service-principal']['tenant-id']}\"\n",
        )

        # Configure ssh key path in main.tf
        TF_LINE_SSH_KEY_PATH = 60
        await _replace_line(
            f"{self.setup_path}/main.tf",
            TF_LINE_SSH_KEY_PATH,
            f"    public_key = file(\"{self.secrets['vm-secrets']['ssh-public-key-path']}\")\n",
        )

        # Configure vm image references in main.tf
        TF_LINE_SOURCE_IMAGE = 68
        if self.use_vm_images:
            await _replace_line(
                f"{self.setup_path}/main.tf",
                TF_LINE_SOURCE_IMAGE,
                "  source_image_id = each.value.source_image_id\n",
            )
            await _delete_lines(
                f"{self.setup_path}/main.tf",
                [
                    line
                    for line in range(
                        TF_LINE_SOURCE_IMAGE + 1, TF_LINE_SOURCE_IMAGE + 6
                    )
                ],
            )

        # Configure vulnbox count in variables.tf
        TF_LINE_COUNT = 2
        await _replace_line(
            f"{self.setup_path}/variables.tf",
            TF_LINE_COUNT,
            f"  default = {self.config['settings']['vulnboxes']}\n",
        )

        # Configure vm image references in variables.tf
        sub_id = self.secrets["cloud-secrets"]["azure-service-principal"][
            "subscription-id"
        ]
        await _insert_after(
            f"{self.setup_path}/variables.tf",
            "    name = string",
            "    subnet_id = number\n"
            + "    size = string\n"
            + "    source_image_id = string\n"
            if self.use_vm_images
            else "",
        )
        await _insert_after(
            f"{self.setup_path}/variables.tf",
            '      name = "engine"',
            f'      subnet_id = {self.config["settings"]["vulnboxes"] + 2}\n'
            + f'      size = "{self.config["setup"]["vm-size"]}"\n'
            + f'      source_image_id = "{self.config["setup"]["vm-image-references"]["engine"].replace("<sub-id>", sub_id)}"\n'
            if self.use_vm_images
            else "",
        )
        await _insert_after(
            f"{self.setup_path}/variables.tf",
            '      name = "checker"',
            f'      subnet_id = {self.config["settings"]["vulnboxes"] + 1}\n'
            + f'      size = "{self.config["setup"]["vm-size"]}"\n'
            + f'      source_image_id = "{self.config["setup"]["vm-image-references"]["checker"].replace("<sub-id>", sub_id)}"\n'
            if self.use_vm_images
            else "",
        )
        await _insert_after(
            f"{self.setup_path}/variables.tf",
            '        name = "vulnbox${vulnbox_id}"',
            f"        subnet_id = vulnbox_id\n"
            + f'        size = "{self.config["setup"]["vm-size"]}"\n'
            + f'        source_image_id = "{self.config["setup"]["vm-image-references"]["vulnbox"].replace("<sub-id>", sub_id)}"\n'
            if self.use_vm_images
            else "",
        )

        # Add terraform outputs for private and public ip addresses
        lines = []
        for vulnbox_id in range(1, self.config["settings"]["vulnboxes"] + 1):
            lines.append(
                f'output "vulnbox{vulnbox_id}" {{\n  value = azurerm_public_ip.vm_pip["vulnbox{vulnbox_id}"].ip_address\n}}\n'
            )
        await _append_lines(f"{self.setup_path}/outputs.tf", lines)

    async def convert_vm_scripts(self):
        # Copy vm script templates for configuration
        await _copy_file(
            f"{self.setup_path}/templates/data/vulnbox.sh",
            f"{self.setup_path}/data/vulnbox.sh",
        )
        await _copy_file(
            f"{self.setup_path}/templates/data/checker.sh",
            f"{self.setup_path}/data/checker.sh",
        )
        await _copy_file(
            f"{self.setup_path}/templates/data/engine.sh",
            f"{self.setup_path}/data/engine.sh",
        )

        # Configure github personal access token
        PAT_LINE = 22
        PAT_LINE_ENGINE = 28
        await _replace_line(
            f"{self.setup_path}/data/vulnbox.sh",
            PAT_LINE,
            f"pat=\"{self.secrets['vm-secrets']['github-personal-access-token']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/data/checker.sh",
            PAT_LINE,
            f"pat=\"{self.secrets['vm-secrets']['github-personal-access-token']}\"\n",
        )
        await _replace_line(
            f"{self.setup_path}/data/engine.sh",
            PAT_LINE_ENGINE,
            f"pat=\"{self.secrets['vm-secrets']['github-personal-access-token']}\"\n",
        )

        # Omit configuration when using vm images
        VULNBOX_CHECKER_CONFIG_LINES_START = 4
        VULNBOX_CHECKER_CONFIG_LINES_END = 21
        ENGINE_CONFIG_LINES_START = 4
        ENGINE_CONFIG_LINES_END = 27
        if self.use_vm_images:
            await _delete_lines(
                f"{self.setup_path}/data/vulnbox.sh",
                [
                    line
                    for line in range(
                        VULNBOX_CHECKER_CONFIG_LINES_START,
                        VULNBOX_CHECKER_CONFIG_LINES_END + 1,
                    )
                ],
            )
            await _delete_lines(
                f"{self.setup_path}/data/checker.sh",
                [
                    line
                    for line in range(
                        VULNBOX_CHECKER_CONFIG_LINES_START,
                        VULNBOX_CHECKER_CONFIG_LINES_END + 1,
                    )
                ],
            )
            await _delete_lines(
                f"{self.setup_path}/data/engine.sh",
                [
                    line
                    for line in range(
                        ENGINE_CONFIG_LINES_START, ENGINE_CONFIG_LINES_END + 1
                    )
                ],
            )

    async def get_ip_addresses(self):
        # Parse ip addresses from ip_addresses.log
        ip_addresses = dict()
        async with aiofiles.open(
            f"{self.setup_path}/logs/ip_addresses.log",
            "r",
        ) as ip_file:
            lines = await ip_file.readlines()
            pattern = r"(\w+)\s*=\s*(.+)"
            for index, line in enumerate(lines):
                m = re.match(pattern, line)
                if m:
                    key = m.group(1)
                    value = m.group(2).strip().replace('"', "")
                    if key == "private_ip_addresses":
                        while "}" not in value:
                            line = lines.pop(index + 1)
                            value += line.strip().replace("=", ":") + ", "
                        value = value[:-2]
                        private_ip_addresses = eval(value)
                    else:
                        ip_addresses[key] = value
        return ip_addresses, private_ip_addresses


class HetznerSetupHelper(Helper):
    def __init__(self, config, secrets):
        self.config = config
        self.secrets = secrets
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        self.setup_path = f"{dir_path}/../../test-setup/{config['setup']['location']}"
        self.use_vm_images = any(
            ref != "" for ref in self.config["setup"]["vm-image-references"].values()
        )

    async def convert_buildscript(self):
        pass

    async def convert_deploy_script(self):
        pass

    async def convert_tf_files(self):
        # Copy terraform file templates for configuration
        await _copy_file(
            f"{self.setup_path}/templates/versions.tf",
            f"{self.setup_path}/versions.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/main.tf",
            f"{self.setup_path}/main.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/variables.tf",
            f"{self.setup_path}/variables.tf",
        )
        await _copy_file(
            f"{self.setup_path}/templates/outputs.tf",
            f"{self.setup_path}/outputs.tf",
        )

        # Add hetzner api token to versions.tf
        TF_LINE_HETZNER_API_TOKEN = 10
        await _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_LINE_HETZNER_API_TOKEN,
            f"  token = \"{self.secrets['cloud-secrets']['hetzner-api-token']}\"\n",
        )

        # Configure ssh key path in main.tf
        TF_LINE_SSH_KEY_PATH = 2
        await _replace_line(
            f"{self.setup_path}/main.tf",
            TF_LINE_SSH_KEY_PATH,
            f"  public_key = file(\"{self.secrets['vm-secrets']['ssh-public-key-path']}\")\n",
        )

        # Add subnet resources to main.tf
        lines = []
        lines.append(
            f'resource "hcloud_network_subnet" "snet" {{\n'
            f'  count = {self.config["settings"]["vulnboxes"] + 2}\n'
            '  type = "cloud"\n'
            + "  network_id = hcloud_network.vnet.id\n"
            + '  network_zone = "eu-central"\n'
            + f'  ip_range = "10.1.${{count.index + 1}}.0/24"\n'
            + "}\n"
        )

        await _insert_after(
            f"{self.setup_path}/main.tf", "############# Subnets #############", lines
        )

        # Add vm resources to main.tf
        lines = []
        lines.append(
            'resource "hcloud_server" "checker_vm" {\n'
            '  name = "checker"\n'
            + f'  server_type = "{self.config["setup"]["vm-size"]}"\n'
            + '  image = "ubuntu-20.04"\n'
            + '  location = "nbg1"\n'
            + "  ssh_keys = [\n  hcloud_ssh_key.ssh_key.id\n  ]\n"
            + f'  network {{\n    network_id = hcloud_network.vnet.id\n    ip = "10.1.{self.config["settings"]["vulnboxes"] + 1}.1"\n  }}\n'
            + f"  depends_on = [\n    hcloud_network_subnet.snet\n  ]\n"
            + "}\n"
        )
        lines.append(
            'resource "hcloud_server" "engine_vm" {\n'
            '  name = "engine"\n'
            + f'  server_type = "{self.config["setup"]["vm-size"]}"\n'
            + '  image = "ubuntu-20.04"\n'
            + '  location = "nbg1"\n'
            + "  ssh_keys = [\n  hcloud_ssh_key.ssh_key.id\n  ]\n"
            + f'  network {{\n    network_id = hcloud_network.vnet.id\n    ip = "10.1.{self.config["settings"]["vulnboxes"] + 2}.1"\n  }}\n'
            + f"  depends_on = [\n    hcloud_network_subnet.snet\n  ]\n"
            + "}\n"
        )
        lines.append(
            'resource "hcloud_server" "vulnbox_vm" {\n'
            f'  count = {self.config["settings"]["vulnboxes"]}\n'
            f'  name = "vulnbox${{count.index + 1}}"\n'
            + f'  server_type = "{self.config["setup"]["vm-size"]}"\n'
            + '  image = "ubuntu-20.04"\n'
            + '  location = "nbg1"\n'
            + "  ssh_keys = [\n  hcloud_ssh_key.ssh_key.id\n  ]\n"
            + f'  network {{\n    network_id = hcloud_network.vnet.id\n    ip = "10.1.${{count.index + 1}}.1"\n  }}\n'
            + f"  depends_on = [\n    hcloud_network_subnet.snet\n  ]\n"
            + "}\n"
        )
        await _insert_after(
            f"{self.setup_path}/main.tf", "############# VMs #############", lines
        )

    async def convert_vm_scripts(self):
        pass

    async def get_ip_addresses(self):
        pass


# TODO:
# - implement
class LocalSetupHelper(Helper):
    def __init__(self, config, secrets):
        self.config = config
        self.secrets = secrets
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        self.setup_path = f"{dir_path}/../../test-setup/{config['setup']['location']}"
        self.use_vm_images = any(
            ref != "" for ref in self.config["setup"]["vm-image-references"].values()
        )

    def convert_buildscript(self):
        pass

    def convert_deploy_script(self):
        pass

    def convert_tf_files(self):
        pass

    def convert_vm_scripts(self):
        pass

    def get_ip_addresses(self):
        pass


class SetupHelper:
    def __init__(self, config, secrets):
        self.config = config
        self.secrets = secrets
        self.helpers = {
            SetupVariant.AZURE: AzureSetupHelper(config, secrets),
            SetupVariant.HETZNER: HetznerSetupHelper(config, secrets),
            SetupVariant.LOCAL: LocalSetupHelper(config, secrets),
        }
        self.team_gen = TeamGenerator(config)

    def generate_teams(self):
        return self.team_gen.generate()

    async def convert_templates(self):
        helper = self.helpers[SetupVariant.from_str(self.config["setup"]["location"])]
        await helper.convert_buildscript()
        await helper.convert_deploy_script()
        await helper.convert_tf_files()
        await helper.convert_vm_scripts()

    async def get_ip_addresses(self):
        helper = self.helpers[SetupVariant.from_str(self.config["setup"]["location"])]
        return await helper.get_ip_addresses()
