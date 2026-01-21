#!/bin/bash

# Not really building bluez-alsa, just installing it from the debian repo

call_chroot "apt update -y &&
  apt install -y bluez bluez-alsa-utils libbluetooth-dev libsbc-dev &&
  cd /usr/bin &&
  wget -t 3 -T 60 --no-check-certificate https://github.com/christianhaitian/RG353VKernel/raw/refs/heads/main/wifibt/rtk_hciattach &&
  cd /lib/firmware &&
  wget -t 3 -T 60 --no-check-certificate https://github.com/christianhaitian/RG353VKernel/raw/refs/heads/main/wifibt/rtl8821c_fw &&
  wget -t 3 -T 60 --no-check-certificate https://github.com/christianhaitian/RG353VKernel/raw/refs/heads/main/wifibt/rtl8821cs_config &&
  cd /home/ark/${CHIPSET}_core_builds &&
  git clone https://github.com/arkq/bluez-alsa.git &&
  cd bluez-alsa &&
  git checkout v4.0.0 &&
  autoreconf --install --force &&
  mkdir build &&
  cd build &&
  ../configure &&
  make -j$(nproc) &&
  cp utils/cli/bluealsa-cli /usr/bin/ &&
  apt remove -y libbluetooth-dev libsbc-dev
  "
sudo cp bluetooth/scripts/Bluetooth.sh Arkbuild/opt/system/
sudo cp bluetooth/scripts/bt* Arkbuild/usr/local/bin/
sudo cp bluetooth/scripts/enable_bluetooth.sh Arkbuild/usr/local/bin/
sudo cp bluetooth/scripts/watchforbtaudio.sh Arkbuild/usr/local/bin/
sudo cp bluetooth/systemd/* Arkbuild/etc/systemd/system/
sudo chmod 777 Arkbuild/usr/local/bin/*
sudo chmod -R 777 Arkbuild/opt/system/
call_chroot "chown -R ark:ark /opt"
call_chroot "systemctl disable watchforbtaudio bluetooth bluealsa enable_bluetooth"
