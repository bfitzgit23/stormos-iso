#!/bin/bash -e
#
##############################################################################
#
#  PostInstall is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your discretion) any later version.
#
#  PostInstall is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
##############################################################################

 name=$(ls -1 /home)
 REAL_NAME=/home/$name

# genfstab -U / > /etc/fstab

#cp /cinnamon-configs/cinnamon-stuff/bin/* /bin/
#cp /cinnamon-configs/cinnamon-stuff/usr/bin/* /usr/bin/
#cp -r /cinnamon-configs/cinnamon-stuff/usr/share/* /usr/share/

mkdir -p /home/$name/.config
mkdir -p /home/$name/.local
mkdir -p /home/$name/Desktop
mkdir -p /home/$name/Music
mkdir -p /home/$name/.oh-my-zsh
mkdir -p /home/$name/.fastfetch

#cp -r /cinnamon-configs/cinnamon-stuff/nemo/* /home/$name/.config/nemo

cp -r /root/.config/* /home/$name/.config/
cp -r /root/.local/* /home/$name/.local 
cp -r /root/.oh-my-zsh/* /home/$name/.oh-my-zsh/
cp /root/.face /home/$name/.face
cp /root/.nanorc /home/$name/.nanorc
cp /root/.profile /home/$name/.profile
cp /root/.xinitrc /home/$name/.xinitrc
cp /root/.xprofile /home/$name/.xprofile
cp /root/.zshrc	   /home/$name/.zshrc
cp -r /root/.fastfetch/* /home/$name/.fastfetch/

mkdir -p /home/$name/.config/autostart

cp -r /root/stormos.png /home/$name/stormos.png

chown -R $name:$name /home/$name/.config
chown -R $name:$name /home/$name/.local
chown -R $name:$name /home/$name/Desktop
chown -R $name:$name /home/$name/Music
chown -R $name:$name /home/$name/.face
chown -R $name:$name /home/$name/.nanorc
chown -R $name:$name /home/$name/.profile
chown -R $name:$name /home/$name/.xinitrc
chown -R $name:$name /home/$name/.xprofile
chown -R $name:$name /home/$name/.zshrc
#mv /middle.png /home/$USER

cp /root/.bashrc /home/$name/.bashrc
cp /root/StormOS.txt /home/$name/StormOS.txt
chown -R $name:$name /home/$name/.bashrc
chown -R $name:$name /home/$name/StormOS.txt

mv /resolv.conf /etc/resolv.conf
chattr +i /etc/resolv.conf
chattr +i /etc/os-release

# create python fix!

#mkdir -p /usr/lib/python3.13/site-packages/six
#touch /usr/lib/python3.13/site-packages/six/__init__.py
#cp /usr/lib/python3.12/site-packages/six.py /usr/lib/python3.13/site-packages/six/six.py

cp /archiso.conf /etc/mkinitcpio.conf.d/archiso.conf

# mkdir /home/$name/.local/share/cinnamon

# cp -r /cinnamon-configs/cinnamon-stuff/extensions /home/$name/.local/share/cinnamon/

plymouth-set-default-theme stormos

rm -rf /home/$name/.config/autostart/calamares.desktop
rm /home/$name/Desktop/calamares.desktop
rm -rf /usr/share/applications/calamares.desktop
