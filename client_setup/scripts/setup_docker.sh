#!/bin/bash

echo -e "\n\nInstalling Docker and requirements...\n"

# This is the reference line for Latex to import the script
# If anything is created before line 8, update the file 'docs/chapters/02_docker_setup.tex'

sudo apt install make docker docker-buildx

echo -e "\n\nSetting Docker permitions\n"

# This is the reference line for Latex to import the script
# If anything is created before line 15, update the file 'docs/chapters/02_docker_setup.tex'

sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker