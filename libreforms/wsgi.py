# a simple wsgi script to run the flask application using gunicorn

from app import app

if __name__ == "__main__":
        app.run()
