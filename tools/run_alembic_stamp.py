from alembic import command
from alembic.config import Config

cfg = Config("/app/alembic.ini")
command.stamp(cfg, "head")
print("STAMP_OK")
