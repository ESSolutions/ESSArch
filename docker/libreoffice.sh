set -se

LibOnrVersion=$(wget -q "https://www.libreoffice.org/download/download" -O - | grep -o -e "/stable/.*/" | cut -d "/" -f 3 | head -n 3 | tail -n 1)
LibOpath="https://download.documentfoundation.org/libreoffice/stable/${LibOnrVersion}/deb/x86_64/"
LibOpackage="LibreOffice_${LibOnrVersion}_Linux_x86-64_deb.tar.gz"
if [ ! -f "${LibOpackage}" ]; then
 echo "Download LibreOffice"
 source="${LibOpath}${LibOpackage}"
 wget $source
else
 echo "Already exists LibreOffice"
fi


tar -xzvf "${LibOpackage}"
cd LibreOffice_*_deb/DEBS
dpkg -i *.deb
