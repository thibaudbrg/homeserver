#!/bin/sh
# Nightly consistent database copies for the NAS backup, run by the db-backup container (compose/db-backup.yml).
# Output: appdata/db-backups (git-ignored), files older than 14 days are removed.
#  - MariaDB: one dump of every database (Nextcloud, Authelia, Guacamole, ...)
#  - SQLite: a clean ".backup" of each file listed in appdata/db-backups/sqlite.list ("name|path under appdata"),
#    safe while the app keeps writing (a plain file copy of a live SQLite/WAL database can be corrupt)
set -u
set -o pipefail
OUT=/backups
TS=$(date +%Y%m%d-%H%M)
fail=0
log() { echo "$(date '+%F %T') $*"; }

if MYSQL_PWD="$(cat /run/secrets/mysql_root_password)" mariadb-dump -h mariadb -u root \
    --all-databases --single-transaction --quick --routines --events --triggers \
    | gzip > "$OUT/mariadb-$TS.sql.gz.part"; then
  mv "$OUT/mariadb-$TS.sql.gz.part" "$OUT/mariadb-$TS.sql.gz"
  log "mariadb ok ($(du -h "$OUT/mariadb-$TS.sql.gz" | cut -f1))"
else
  rm -f "$OUT/mariadb-$TS.sql.gz.part"; log "mariadb FAILED"; fail=1
fi

if [ -f "$OUT/sqlite.list" ]; then
  while IFS='|' read -r name rel; do
    case "$name" in ''|\#*) continue ;; esac
    if sqlite3 "/appdata/$rel" ".backup '$OUT/$name-$TS.sqlite3'" && gzip -f "$OUT/$name-$TS.sqlite3"; then
      log "$name ok"
    else
      rm -f "$OUT/$name-$TS.sqlite3"; log "$name FAILED ($rel)"; fail=1
    fi
  done < "$OUT/sqlite.list"
fi

find "$OUT" -maxdepth 1 -name '*.gz' -mtime +14 -delete
chown -R "$PUID:$PGID" "$OUT"
log "done (fail=$fail)"
exit $fail
