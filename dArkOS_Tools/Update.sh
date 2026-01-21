#!/bin/bash

if [[ "$(stat -c "%U" /home/ark)" != "ark" ]]; then
  printf "Fixing home folder permissions.  Please wait..."
  sudo chown -R ark:ark /home/ark
  sudo chmod -R 755 /home/ark
fi

printf "\nChecking for updates.  Please wait..."

LOG_FILE="/home/ark/esupdate.log"

if [ -f "$LOG_FILE" ]; then
  sudo rm "$LOG_FILE"
fi

sudo timedatectl set-ntp 1

LOCATION="https://raw.githubusercontent.com/tehhoffman/HoffmanOS-Updates/master"

wget -t 3 -T 60 --no-check-certificate "$LOCATION"/LICENSE -O /dev/shm/LICENSE -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  sudo msgbox "Looks like OTA updating is currently down or your wifi or internet connection is not functioning correctly."
  printf "There was an error with attempting this update." | tee -a "$LOG_FILE"
  exit 1
fi

# Best-effort "no updates" detection:
# If the updates repo exposes a version marker (recommended: `.VERSION` containing the build date),
# compare it against the device's local version and exit early if they match.
LOCAL_VERSION=""
REMOTE_VERSION=""

if [ -f /home/ark/.config/.VERSION ]; then
  LOCAL_VERSION="$(tr -d '\r\n' </home/ark/.config/.VERSION)"
elif [ -f /usr/share/plymouth/themes/text.plymouth ]; then
  # Fallback: use the title string shown on boot (ex: "HoffmanOS (YYYY.MM.DD)")
  LOCAL_VERSION="$(grep -m 1 '^title=' /usr/share/plymouth/themes/text.plymouth | cut -d'=' -f2- | tr -d '\r\n')"
fi

wget -q -t 2 -T 20 --no-check-certificate "$LOCATION"/.VERSION -O /dev/shm/.VERSION_REMOTE -a "$LOG_FILE"
if [ $? -eq 0 ]; then
  REMOTE_VERSION="$(tr -d '\r\n' </dev/shm/.VERSION_REMOTE)"
else
  # Fallback: if `.VERSION` isn't hosted, try comparing the plymouth title (if the repo hosts it).
  wget -q -t 2 -T 20 --no-check-certificate "$LOCATION"/text.plymouth -O /dev/shm/text.plymouth.remote -a "$LOG_FILE"
  if [ $? -eq 0 ]; then
    REMOTE_VERSION="$(grep -m 1 '^title=' /dev/shm/text.plymouth.remote | cut -d'=' -f2- | tr -d '\r\n')"
  fi
fi

if [ -n "$LOCAL_VERSION" ] && [ -n "$REMOTE_VERSION" ] && [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ]; then
  sudo msgbox "No updates are currently available."
  exit 0
fi

wget -t 3 -T 60 --no-check-certificate "$LOCATION"/HoffmanOSUpdate.sh -O /home/ark/HoffmanOSUpdate.sh -a "$LOG_FILE" || sudo rm -f /home/ark/HoffmanOSUpdate.sh | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  sudo msgbox "Looks like OTA updating is currently down or your wifi or internet connection is not functioning correctly."
  printf "There was an error with attempting this update." | tee -a "$LOG_FILE"
  exit 1
fi

sudo chmod -v 777 /home/ark/HoffmanOSUpdate.sh | tee -a "$LOG_FILE"
/home/ark/HoffmanOSUpdate.sh

if [ $? -ne 187 ]; then
  sudo msgbox "There was an error with attempting this update.  Did you make sure to enable your wifi and connect to a wifi network?  If so, enable remote services in options and try to update again."
  printf "There was an error with attempting this update." | tee -a "$LOG_FILE"
  if [ -f /home/ark/HoffmanOSUpdate.sh ]; then
    rm /home/ark/HoffmanOSUpdate.sh
  fi
fi

if [ ! -z $(pidof rg351p-js2xbox) ]; then
  sudo kill -9 $(pidof rg351p-js2xbox)
  sudo rm /dev/input/by-path/platform-odroidgo2-joypad-event-joystick
fi
