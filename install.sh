#!/bin/bash
echo -e "\033[1;92m[*] DEPLOYING ROAD DAWG (FINAL)...\033[0m"

# DIRECTORY IS CURRENT DIR (GIT REPO)
MAIN_DIR="$HOME/RoadDawg"
mkdir -p "$MAIN_DIR/storage"
mkdir -p "$MAIN_DIR/system"

# Ensure venv exists
if [ ! -d "$MAIN_DIR/system/.venv" ]; then
    echo -e "[*] Creating VENV..."
    python3 -m venv "$MAIN_DIR/system/.venv"
fi

"$MAIN_DIR/system/.venv/bin/pip" install flask flask-cors pyperclip

# CREATE LAUNCHER
cat << 'RUN' > run_road_dawg.sh
#!/bin/bash
echo -e "\033[1;96m[💀] HUNTING ZOMBIES...\033[0m"
fuser -k 5575/tcp > /dev/null 2>&1
pkill -f "road_dawg.py" > /dev/null 2>&1

echo -e "\033[1;92m[✔] SECTOR CLEAR. LAUNCHING...\033[0m"
"$HOME/RoadDawg/system/.venv/bin/python3" "$HOME/RoadDawg/server/road_dawg.py"
RUN
chmod +x run_road_dawg.sh

echo -e "\n\033[1;92m[✔] INSTALLED.\033[0m"
echo -e "Run: ./run_road_dawg.sh"
