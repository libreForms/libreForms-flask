""" 
wsgi/__init__.py: simple wsgi script to run the flask application using gunicorn

"""

__name__ = "wsgi"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.6.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app import create_app

# initialize the app
app = create_app()

if __name__ == "__main__":
        app.run()



