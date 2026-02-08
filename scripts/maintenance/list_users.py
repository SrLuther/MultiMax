import json

from multimax.models import User

if __name__ == "__main__":
    users = User.query.all()
    print(
        json.dumps(
            [{"id": user.id, "username": user.username, "name": user.name, "active": user.active} for user in users]
        )
    )
