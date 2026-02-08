from alembic import command
from alembic.config import Config

cfg = Config("/app/alembic.ini")
command.upgrade(cfg, "head")
print("UPGRADE_OK")
