wifi-connection.sh

pacman -Sy 

sudo pacman -S calamares-config-xfce --noconfirm --overwrite '*'
sudo pacman -S calamares-config-xfce --noconfirm --overwrite '*'

sudo calamares -d 8 > /root/calamares.log


