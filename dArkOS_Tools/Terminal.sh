#!/bin/bash

set -u

CUR_TTY="/dev/tty1"
DEFAULT_DIR="/home/ark"
TERMINAL_BIN="/opt/inttools/terminal_osk.py"
LOG_DIR="/home/ark/.config"
LOG_FILE="${LOG_DIR}/terminal_osk.log"

sudo chmod 666 "${CUR_TTY}"
export TERM=linux
export XDG_RUNTIME_DIR="/run/user/${UID}/"

reset
printf "\e[?25l" > "${CUR_TTY}"

if [[ ! -e "/dev/input/by-path/platform-odroidgo2-joypad-event-joystick" ]]; then
  if test ! -z "$(tr -d '\0' < /home/ark/.config/.DEVICE | grep RGB20PRO)"
  then
    sudo setfont /usr/share/consolefonts/Lat7-TerminusBold32x16.psf.gz
  else
    sudo setfont /usr/share/consolefonts/Lat7-TerminusBold28x14.psf.gz
  fi
else
  sudo setfont /usr/share/consolefonts/Lat7-Terminus16.psf.gz
fi

dpkg -s "python3-urwid" &>/dev/null
if [ "$?" != "0" ]; then
  echo "Installing the python3 urwid module needed for this.  Please wait..." 2>&1 > "${CUR_TTY}"
  sudo dpkg -i --force-all /opt/inttools/python3-urwid_2.0.1-2build2_arm64.deb
fi

StartControls() {
  sudo chmod 666 /dev/uinput
  export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
  if [[ ! -z $(pgrep -f gptokeyb) ]]; then
    pgrep -f gptokeyb | sudo xargs kill -9
  fi
  /opt/inttools/gptokeyb -1 "python3" -c "/opt/inttools/keys.gptk" > /dev/null 2>&1 &
  disown
}

StopControls() {
  if [[ ! -z $(pgrep -f gptokeyb) ]]; then
    pgrep -f gptokeyb | sudo xargs kill -9
  fi
  unset SDL_GAMECONTROLLERCONFIG_FILE
}

ExitMenu() {
  printf "\033c" > "${CUR_TTY}"
  StopControls
  if [[ ! -e "/dev/input/by-path/platform-odroidgo2-joypad-event-joystick" ]]; then
    sudo setfont /usr/share/consolefonts/Lat7-Terminus20x10.psf.gz
  fi
  reset
  exit 0
}

printf "\033c" > "${CUR_TTY}"
printf "Starting Terminal. Please wait..." > "${CUR_TTY}"

StartControls
trap ExitMenu EXIT

mkdir -p "${LOG_DIR}"

if [[ ! -f "${TERMINAL_BIN}" ]]; then
  printf "\nMissing ${TERMINAL_BIN}\n" > "${CUR_TTY}"
  printf "Copy terminal_osk.py to /opt/inttools/ and retry.\n" > "${CUR_TTY}"
  sleep 5
  exit 1
fi

printf "\n\n=== terminal_osk start: $(date) ===\n" >> "${LOG_FILE}"

if [[ -x "${TERMINAL_BIN}" ]]; then
  "${TERMINAL_BIN}" "${DEFAULT_DIR}" 2>> "${LOG_FILE}"
else
  python3 "${TERMINAL_BIN}" "${DEFAULT_DIR}" 2>> "${LOG_FILE}"
fi

exit_code=$?
if [[ ${exit_code} -ne 0 ]]; then
  printf "\nTerminal failed to start (exit ${exit_code}).\n" > "${CUR_TTY}"
  printf "Log: ${LOG_FILE}\n" > "${CUR_TTY}"
  sleep 5
fi
