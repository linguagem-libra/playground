from flask import Flask, render_template
from routes import register_routes

def create_app():
    app = Flask(__name__)
    register_routes(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
