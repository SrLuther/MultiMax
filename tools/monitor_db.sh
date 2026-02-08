#!/bin/sh
# Monitor que verifica logs da API e reinicia o Postgres com backup se houver muitos erros
THRESH=3
WINDOW=5m
BACKUP_DIR=/opt/multimax/backups
LOGFILE=/opt/multimax/scripts/monitor_db.log
mkdir -p "$BACKUP_DIR"
while true; do
  COUNT=$(docker logs --since "$WINDOW" multimax 2>&1 | grep -E -i "Database Error|OperationalError|connection failed|psycopg" | wc -l)
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') count=$COUNT" >> "$LOGFILE"
  if [ "$COUNT" -ge "$THRESH" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    echo "$(date -u) - Threshold reached: $COUNT -> backing up and restarting Postgres" >> "$LOGFILE"
    docker exec -i multimax-postgres pg_dump -U multimax multimax | gzip > "$BACKUP_DIR/multimax_monitor_${TIMESTAMP}.sql.gz"
    echo "$(date -u) - Backup created: $BACKUP_DIR/multimax_monitor_${TIMESTAMP}.sql.gz" >> "$LOGFILE"
    docker restart multimax-postgres
    # wait for ready
    for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
      if docker exec multimax-postgres pg_isready -U multimax >/dev/null 2>&1; then
        echo "$(date -u) - Postgres is ready" >> "$LOGFILE"
        break
      fi
      sleep 5
    done
    echo "$(date -u) - Action completed" >> "$LOGFILE"
    # cooldown to avoid repeated restarts
    sleep 300
  fi
  sleep 30
done
