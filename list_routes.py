import sys

from multimax import create_app

sys.path.insert(0, "/app")

app = create_app()
routes = [rule.rule for rule in app.url_map.iter_rules()]
print("Rotas disponíveis (primeiras 20):")
for route in routes[:20]:
    print(route)
