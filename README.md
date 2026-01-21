# <p align="center">Welcome to HoffmanOS</p>

### <p align="center">Debian based version of the HoffmanOS operating system for select RK3326 and RK3566 based portable gaming devices.</p>

**Building instructions:**
   - Suggested Environment - Ubuntu or related variants, version 24.04 or newer.  Windows Subsystem for Linux (WSL) is not supported and will not work due to no support for chroot. \
     Because chroot is used in this process, heavy use of sudo is made.  To reduce the possibility of priviledge issues, \
     it's best to be able to execute sudo without needing a password.  This can be done using one of the 2 methods below.
      - Method 1: - Open a Terminal window and type `sudo visudo` \
                    In the bottom of the file, add the following line: `$USER ALL=(ALL) NOPASSWD: ALL` \
                    Where $USER is your username on your system. Save and close the sudoers file (if you haven't changed your \
                    default terminal editor (you'll know if you have), press Ctl + x to exit nano and it'll prompt you to save).
      - Method 2: - Clone this git repo then run `./FreeSudo.sh`.  If there were no errors, it should've completed this change for you. \
                    You can verify this by checking if a `/etc/sudoers.d/$USER` file exists and contains `$USER ALL=(ALL) NOPASSWD: ALL` in it.
     
This is a forked and customized distribution of dArkOS from christianhaitian (https://github.com/christianhaitian/dArkOS)

The goal of this distribution is to remove all potential bloat while simultaneously adding tools that enable users to add exactly what they wish to their system without the need for re-flashing. The primary focus will be on the RG503 device, rk3566 chipset, but I intent to continue to make the updates compatible with all versions for the foreseeable future.

Now you should be able to just run make <device_name> to build for a supported device.  Example: `make rg353m`

**Notes**
- To build on a different release of Debian, change the DEBIAN_CODE_NAME export in the Makefile or add DEBIAN_CODE_NAME=<release> as a variable to `make`.  Other debian code names can be found at https://www.debian.org/releases/
- By default, this will build with both a 64bit and 32bit userspace.  This is primarily to support some 32bit ports available through PortMaster.  There are also some 32bit retroarch emulators available but the performance seems to be similar to the 64bit retroarch emulators at this point.
 - To build without 32bit support, change the BUILD_ARMHF export in the Makefile to n or add BUILD_ARMHF=n as a variable to `make`.
- For RK3566, you can add Kodi to your build.  Just change the BUILD_KODI export in the Makefile to y or add BUILD_KODI=y as a variavble to `make`.  Kodi is also available as a prepackaged build in the extra_packages/rk3566 subfolder.  Just copy it to your tools folder and launch from Options/Tools in the start menu.
 - Be aware that building Kodi will add a significant amount of time to your build.  Could be double or triple the build time.
- Initial build time on an Intel I7-8700 65w unit with a 512GB NVME SSD and 32GB of DDR4 memory is a little over 19 hours.  Subsequent builds are about 3 hours thanks to ccache.
