#!/bin/bash
printf "\033c" >> /dev/tty1
if compgen -G "/boot/rk3566*" > /dev/null; then
  if test ! -z "$(cat /home/ark/.config/.DEVICE | grep RGB20PRO | tr -d '\0')"
  then
    sudo setfont /usr/share/consolefonts/Lat7-TerminusBold32x16.psf.gz
  else
    sudo setfont /usr/share/consolefonts/Lat7-TerminusBold28x14.psf.gz
  fi
  height="20"
  width="60"
fi
sudo systemctl enable batt_led
sudo systemctl start batt_led
printf "\n\n\n\e[32mLow battery warning has been enabled.\n"
sudo cp /usr/local/bin/Disable\ Low\ Battery\ Warning.sh /opt/system/Advanced/.
sudo rm /opt/system/Advanced/Enable\ Low\ Battery\ Warning.sh
sleep 2
printf "\033c" >> /dev/tty1
sudo systemctl restart emulationstation
