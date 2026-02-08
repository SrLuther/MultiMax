#!/bin/sh
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP=/backups/multimax_${TIMESTAMP}.sql
echo "Starting pg_dump to $BACKUP"
docker exec multimax-postgres sh -lc "pg_dump -U multimax multimax > ${BACKUP}"
docker exec multimax-postgres sh -lc "gzip -f ${BACKUP}"
echo "Backup created: ${BACKUP}.gz"
COUNT=$(docker logs --since 5m multimax 2>&1 | grep -E -i "Database Error|OperationalError|connection failed|psycopg" | wc -l)
echo "Errors in last 5m: $COUNT"
if [ "$COUNT" -ge 3 ]; then
  echo "Threshold reached ($COUNT >=3) — creating another backup and restarting postgres"
  TIMESTAMP2=$(date +%Y%m%d_%H%M%S)
  docker exec multimax-postgres sh -lc "pg_dump -U multimax multimax > /backups/multimax_${TIMESTAMP2}.sql && gzip -f /backups/multimax_${TIMESTAMP2}.sql"
  echo "Backup before restart created: /backups/multimax_${TIMESTAMP2}.sql.gz"
  docker restart multimax-postgres
  sleep 5
  docker exec multimax-postgres pg_isready -U multimax
  echo "Postgres restarted"
else
  echo "Threshold not reached, no restart performed"
fi
