#!/bin/bash

# --- CONFIGURACIÓN ---
SCRIPT_NAME="gemini_terminal.py"
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/venv"
BASHRC="$HOME/.bashrc"

echo "===================================================="
echo "   GEMINI CLI - FULL AUTOMATED SETUP (LINUX)        "
echo "===================================================="

# 1. Instalar dependencias del sistema
echo "[*] Step 1: Installing system dependencies (xclip)..."
sudo apt-get update && sudo apt-get install -y xclip python3-venv

# 2. Crear entorno virtual
echo "[*] Step 2: Creating virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv venv
    echo "[+] Virtual environment created."
else
    echo "[i] Virtual environment already exists. Skipping."
fi

# 3. Instalar dependencias de Python
echo "[*] Step 3: Installing Python libraries..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install google-genai Pillow pyperclip

# 4. Configurar Aliases en .bashrc
echo "[*] Step 4: Configuring aliases in .bashrc..."

# Definimos los comandos
ALIAS_F="alias gemf='$VENV_PATH/bin/python $PROJECT_DIR/$SCRIPT_NAME -f'"
ALIAS_T="alias gemt='$VENV_PATH/bin/python $PROJECT_DIR/$SCRIPT_NAME -t'"

# Verificamos si ya existen para no duplicar
if grep -q "alias gemf=" "$BASHRC"; then
    echo "[i] Alias 'gemf' already exists in .bashrc. Updating..."
    sed -i "/alias gemf=/c\\$ALIAS_F" "$BASHRC"
else
    echo "$ALIAS_F" >> "$BASHRC"
fi

if grep -q "alias gemt=" "$BASHRC"; then
    echo "[i] Alias 'gemt' already exists in .bashrc. Updating..."
    sed -i "/alias gemt=/c\\$ALIAS_T" "$BASHRC"
else
    echo "$ALIAS_T" >> "$BASHRC"
fi

echo "===================================================="
echo " ✅ INSTALLATION COMPLETE!"
echo "===================================================="
echo " IMPORTANT: Run the following command to apply changes:"
echo " source ~/.bashrc"
echo ""
echo " After that, you can use:"
echo " >> gemf (Flash Mode)"
echo " >> gemt (Pro Mode)"
echo "===================================================="