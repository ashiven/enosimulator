#! /usr/bin/env bash

set -euo pipefail

echo -e "\033[32m[+] Installing necessary dependencies..."
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" |
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo apt-get install -y docker-compose-plugin
export DOCKER_BUILDKIT=0

pat=_placeholder_

optional() {
  directory="$1"
  if [ ! -d "$directory" ]; then
    "${@:2}"
  fi
}

retry() {
  local retries=3
  until "$@" || [ "$retries" -eq 0 ]; do
    echo -e "\033[31m[!] Retrying command ...\033[0m"
    sleep 1
    retries=$((retries - 1))
  done
}

sed -i 's/^[[:space:]]*//;s/[[:space:]]*$//' services.txt
if [ -d "../packer" ]; then
  sudo mv services.txt ../packer
  cd ../packer
fi

while read -r service_name; do
  optional "${service_name}" sudo git clone "https://${pat}@github.com/enowars/${service_name}.git"
  sudo find "${service_name}" \( -name "requirements*" -o -name "Dockerfile*" \) -exec sed -i "s|enochecker3[^ ]*|git+https://github.com/ashiven/enochecker3|g" "{}" \;

  cd "${service_name}/service"
  echo -e "\033[32m[+] Starting ${service_name}-service...\033[0m"
  retry sudo docker compose up --build --force-recreate -d

  cd "../checker"
  echo -e "\033[32m[+] Starting ${service_name}-exploiter...\033[0m"
  retry sudo docker compose up --build --force-recreate -d
  cd ..

done <"services.txt"