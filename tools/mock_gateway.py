import logging

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json(silent=True) or {}
    app.logger.info(f"/notify payload: {data}")
    # Simula sucesso do envio
    return jsonify({"ok": True, "received": bool(data)}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3001)
