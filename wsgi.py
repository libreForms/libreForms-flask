# a simple wsgi script to run the flask application using gunicorn

from app import create_app

app = create_app()

if __name__ == "__main__":
        app.run()
