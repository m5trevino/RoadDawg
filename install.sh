#!/bin/bash
echo -e "\033[1;92m[*] DEPLOYING ROAD DAWG v2.0...\033[0m"

MAIN_DIR="$HOME/road_dawg"
mkdir -p "$MAIN_DIR/storage"
mkdir -p "$MAIN_DIR/system"

cp server/road_dawg.py "$MAIN_DIR/system/"

echo -e "[*] Creating VENV..."
python3 -m venv "$MAIN_DIR/system/.venv"
"$MAIN_DIR/system/.venv/bin/pip" install flask flask-cors pyperclip

cat << 'RUN' > run_road_dawg.sh
#!/bin/bash
"$HOME/road_dawg/system/.venv/bin/python3" "$HOME/road_dawg/system/road_dawg.py"
RUN
chmod +x run_road_dawg.sh

echo -e "\n\033[1;92m[✔] INSTALLED.\033[0m"
echo -e "Run: ./run_road_dawg.sh"
