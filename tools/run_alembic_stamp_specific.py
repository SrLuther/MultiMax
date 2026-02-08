from alembic import command
from alembic.config import Config

cfg = Config("/app/alembic.ini")
command.stamp(cfg, "010")
print("STAMPED_010")
