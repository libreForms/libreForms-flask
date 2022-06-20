# a simple wsgi script to run the flask application using gunicorn

from app import create_app

application = create_app()

if __name__ == "__main__":
        application.run()
