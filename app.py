import os
from multimax import create_app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    try:
        from waitress import serve
    except ImportError:
        serve = None
    if serve:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=debug)
