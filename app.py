from flask import Flask
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev_secret_key'

    register_blueprints(app)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=8000)
