#!/bin/bash
echo -e "\033[1;96m[💀] HUNTING ZOMBIES...\033[0m"
fuser -k 5575/tcp > /dev/null 2>&1
pkill -f "road_dawg.py" > /dev/null 2>&1

echo -e "\033[1;92m[✔] SECTOR CLEAR. LAUNCHING...\033[0m"
"$HOME/RoadDawg/system/.venv/bin/python3" "$HOME/RoadDawg/server/road_dawg.py"
