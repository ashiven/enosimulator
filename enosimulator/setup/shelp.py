import asyncio
import concurrent.futures
import os
import re
from abc import ABC, abstractmethod
from enum import Enum

import aiofiles
from teamgen import TeamGenerator


class SetupVariant(Enum):
    AZURE = "azure"
    LOCAL = "local"

    @staticmethod
    def from_str(s):
        if s == "azure":
            return SetupVariant.AZURE
        elif s == "local":
            return SetupVariant.LOCAL
        else:
            raise NotImplementedError


####  Helpers ####


async def _async_exec(f, *args, **kwargs):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, f, *args, **kwargs)


async def _copy_file(src, dst):
    async def path_exists(src):
        return os.path.exists(src)

    if await path_exists(src):
        async with aiofiles.open(src, "rb") as src_file:
            async with aiofiles.open(dst, "wb") as dst_file:
                await dst_file.write(src_file.read())


async def _replace_line(path, line_number, new_line):
    async with aiofiles.open(path, "rb+") as file:
        lines = await file.readlines()
        lines[line_number] = new_line.replace("\\", "/").encode("utf-8")
        await file.seek(0)
        await file.writelines(lines)
        await file.truncate()


async def _insert_after(path, after, insert_lines):
    new_lines = []
    async with open(path, "rb") as file:
        lines = await file.readlines()
        for line in lines:
            new_lines.append(line)
            if line.startswith(after.encode("utf-8")):
                for insert_line in insert_lines:
                    new_lines.append(insert_line.encode("utf-8"))
    async with aiofiles.open(path, "wb") as file:
        await file.writelines(new_lines)


async def _append_lines(path, append_lines):
    async with open(path, "ab") as file:
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


async def _dirname(path):
    async def os_dirname(path):
        return os.path.dirname(path)

    return await _async_exec(os_dirname, path)


async def _abspath(path):
    async def os_abspath(path):
        return os.path.abspath(path)

    return await _async_exec(os_abspath, path)


#### End Helpers ####


class Helper(ABC):
    @abstractmethod
    def convert_buildscript(self):
        pass

    @abstractmethod
    def convert_deploy_script(self):
        pass

    @abstractmethod
    def convert_tf_files(self):
        pass

    @abstractmethod
    def convert_vm_scripts(self):
        pass

    @abstractmethod
    def get_ip_addresses(self):
        pass


class AzureSetupHelper(Helper):
    async def __init__(self, config, secrets, setup_path):
        self.config = config
        self.secrets = secrets
        self.setup_path = setup_path
        self.use_vm_images = False

    @classmethod
    async def new(cls, config, secrets):
        dir_path = await _dirname(await _abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        setup_path = f"{dir_path}/../test-setup/{config['setup']['location']}"
        return cls(config, secrets, setup_path)

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
                f'vulnbox{vulnbox_id}_ip=$(grep -oP "vulnbox{vulnbox_id}\s*=\s*\K[^\s]+" ./logs/ip_addresses.log)\n'
            )
        await _insert_after(f"{self.setup_path}/build.sh", "engine_ip=", lines)

        # Configure writing ssh config
        lines = []
        for vulnbox_id in range(1, self.config["settings"]["vulnboxes"] + 1):
            lines.append(
                f'echo -e "Host vulnbox{vulnbox_id}\\nUser groot\\nHostName ${{vulnbox{vulnbox_id}_ip}}\\nIdentityFile ${{ssh_private_key_path}}\\nStrictHostKeyChecking no\\n" >>${{ssh_config}}\n'
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
            f'setup_path="{await _abspath(self.setup_path)}"\n',
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
                f'echo -e "\\033[31;33m[!] This will take a few minutes. Please be patient.\\033[0m"\n'
            )
            lines.append(
                f'retry ssh -F ${{ssh_config}} vulnbox{vulnbox_id} "chmod +x vulnbox.sh && ./vulnbox.sh" | tee ./logs/vulnbox{vulnbox_id}_config.log 2>&1\n'
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
        _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_CLIENT_SECRET_LINE,
            f"  client_secret   = \"{self.secrets['cloud-secrets']['azure-service-principal']['client-secret']}\"\n",
        )
        _replace_line(
            f"{self.setup_path}/versions.tf",
            TF_TENANT_ID_LINE,
            f"  tenant_id       = \"{self.secrets['cloud-secrets']['azure-service-principal']['tenant-id']}\"\n",
        )

        # Configure ssh key path in main.tf
        TF_LINE_SSH_KEY_PATH = 61
        await _replace_line(
            f"{self.setup_path}/main.tf",
            TF_LINE_SSH_KEY_PATH,
            f"    public_key = file(\"{self.secrets['vm-secrets']['ssh-public-key-path']}\")\n",
        )

        # Configure vm image references in main.tf
        TF_LINE_SOURCE_IMAGE = 69
        if any(
            ref != "<optional>"
            for ref in self.config["setup"]["vm-image-references"].values()
        ):
            self.use_vm_images = True
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
        if self.use_vm_images:
            sub_id = self.secrets["cloud-secrets"]["azure-service-principal"][
                "subscription-id"
            ]
            await _insert_after(
                f"{self.setup_path}/variables.tf",
                "    name = string",
                f"    source_image_id = string\n",
            )
            await _insert_after(
                f"{self.setup_path}/variables.tf",
                '      name = "engine"',
                f'      source_image_id = "{self.config["setup"]["vm-image-references"]["engine"].replace("<sub-id>", sub_id)}"\n',
            )
            await _insert_after(
                f"{self.setup_path}/variables.tf",
                '      name = "checker"',
                f'      source_image_id = "{self.config["setup"]["vm-image-references"]["checker"].replace("<sub-id>", sub_id)}"\n',
            )
            await _insert_after(
                f"{self.setup_path}/variables.tf",
                '        name = "vulnbox${vulnbox_id}"',
                f'        source_image_id = "{self.config["setup"]["vm-image-references"]["vulnbox"].replace("<sub-id>", sub_id)}"\n',
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


# TODO:
# - implement
class LocalSetupHelper(Helper):
    async def __init__(self, config, secrets):
        self.config = config
        self.secrets = secrets
        dir_path = await _dirname(await _abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        self.setup_path = f"{dir_path}/../test-setup/{config['setup']['location']}"

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
    def __init__(self, config, secrets, helpers):
        self.config = config
        self.secrets = secrets
        self.helpers = helpers
        self.team_gen = TeamGenerator(config)

    @classmethod
    async def new(cls, config, secrets):
        dir_path = await _dirname(await _abspath(__file__))
        dir_path = dir_path.replace("\\", "/")
        helpers = {
            SetupVariant.AZURE: await AzureSetupHelper.new(config, secrets),
            SetupVariant.LOCAL: await LocalSetupHelper.new(config, secrets),
        }
        return cls(config, secrets, helpers)

    async def convert_templates(self):
        helper = self.helpers[SetupVariant.from_str(self.config["setup"]["location"])]
        await helper.convert_buildscript()
        await helper.convert_deploy_script()
        await helper.convert_tf_files()
        await helper.convert_vm_scripts()

    async def get_ip_addresses(self):
        helper = self.helpers[SetupVariant.from_str(self.config["setup"]["location"])]
        return await helper.get_ip_addresses()

    def generate_teams(self):
        return self.team_gen.generate()
