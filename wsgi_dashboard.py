#!/usr/bin/env python
# Kyle Fitzsimmons, 2016
'''WSGI entry script for allowing API to be managed by gunicorn'''
from dashboard.server import create_app

application = app = create_app()


if __name__ == "__main__":
    if app.config.get('CONF') in ['development', 'testing']:
        app.run(host=app.config['APP_HOST'],
                port=app.config['APP_PORT'],
                debug=True)
    else:
        app.run(port=app.config['APP_PORT'])
