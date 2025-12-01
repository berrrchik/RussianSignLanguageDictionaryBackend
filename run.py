#!/usr/bin/env python3
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)

