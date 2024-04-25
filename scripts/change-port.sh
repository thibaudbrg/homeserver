#!/bin/bash
HTTP_PORT=81
HTTPS_PORT=444
BACKUP_FILES=true
BACKUP_DIR="/volume1/apps/free_ports/backup"
DELETE_OLD_BACKUPS=false
KEEP_BACKUP_DAYS=30
DATE=$(date +%Y-%m-%d-%H-%M-%S)
CURRENT_BACKUP_DIR="$BACKUP_DIR/$DATE"

echo "Starting port change script at $DATE"

if [ "$BACKUP_FILES" = "true" ]; then
  echo "Backing up configuration files..."
  mkdir -p "$CURRENT_BACKUP_DIR"
  cp /usr/syno/share/nginx/*.mustache "$CURRENT_BACKUP_DIR" && echo "Backup successful."
fi

if [ "$DELETE_OLD_BACKUPS" = "true" ]; then
  echo "Deleting backups older than $KEEP_BACKUP_DAYS days..."
  find "$BACKUP_DIR/" -type d -mtime +$KEEP_BACKUP_DAYS -exec rm -r {} \; && echo "Old backups deleted."
fi

echo "Changing HTTP and HTTPS ports..."


# For HTTP
sed -i "s/^\([ \t]*listen[ \t]*\)\([[]::[]]:\)80\([^0-9]\)/\1\2$HTTP_PORT\3/" /usr/syno/share/nginx/*.mustache

# For HTTPS
sed -i "s/^\([ \t]*listen[ \t]*\)\([[]::[]]:\)443\([^0-9]\)/\1\2$HTTPS_PORT\3/" /usr/syno/share/nginx/*.mustache



echo "Changes made, outputting differences:"
diff /usr/syno/share/nginx/ $CURRENT_BACKUP_DIR 2>&1 | tee $CURRENT_BACKUP_DIR/changes.log

# Check if the changes are actually in the files
grep -ri "listen $HTTP_PORT" /usr/syno/share/nginx/ && echo "HTTP port changed."
grep -ri "listen $HTTPS_PORT" /usr/syno/share/nginx/ && echo "HTTPS port changed."

# Perform nginx reload if running on DSM 7.X
if grep -q 'majorversion="7"' "/etc.defaults/VERSION"; then
  echo "Detected DSM 7.X, reloading nginx..."
  synosystemctl restart nginx
  if [ $? -eq 0 ]; then
    echo "Nginx reloaded successfully."
  else
    echo "Failed to reload Nginx."
  fi
else
  echo "No need to reload nginx."
fi

# Final check to confirm if Nginx is listening on the new ports
netstat -tulpn | grep '80\|443' && echo "Nginx is still listening on the old ports." || echo "Port change successful."

echo "Script completed."

