#!/bin/bash

# ===============================================================
# Ce script est à lancer après chaque mise à jour du CMS
# pour faire en sorte que les fichiers ne soient pas reset
# par le processus de mise à jour d'Azuriom.
#
# À lancer uniquement si vous avez besoin de modifier
# les fichier du CMS pour des besoins spécifiques.
# ===============================================================

CMS_FILES=/home/debian/cms_files
AZURIOM_PATH=/var/www/azuriom
BACKUP_PATH=/home/debian/backups

/usr/bin/cp -drf $AZURIOM_PATH $BACKUP_PATH/backup_$(date +"%Y-%m-%d_%H-%M-%S")
/usr/bin/cp -drf $CMS_FILES/* $AZURIOM_PATH

/usr/bin/chown -R www-data:www-data $AZURIOM_PATH
/usr/bin/chown -R debian:debian /home/debian
/usr/bin/chmod -R 755 $AZURIOM_PATH

/usr/bin/systemctl restart apache2.service