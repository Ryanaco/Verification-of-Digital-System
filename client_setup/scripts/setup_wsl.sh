#!/bin/bash

echo -e "\nUpdating system...\n"

# This is the reference line for Latex to import the script
# If anything is created before line 7, update the file 'docs/chapters/02_wsl_setup.tex'

sudo apt -y update
sudo apt -y upgrade
sudo apt install -y --no-install-recommends