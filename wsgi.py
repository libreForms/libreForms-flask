# a simple wsgi script to run the flask application using gunicorn

from app import create_app, db, create_app, models

# initialize the database
db.create_all(app=create_app())

# initialize the app
app = create_app()

if __name__ == "__main__":
        app.run()
