""" 
cli.py: CLI commands for managing the web application


This script is initially described in the following github issue:
https://github.com/libreForms/libreForms-flask/issues/123.

"""

__name__ = "app.views.cli"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.7.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import Blueprint
from flask.cli import with_appcontext
import click

bp = Blueprint('cli', __name__)

@bp.cli.command('create')
@click.argument('username')
@with_appcontext
def create_user(username):
    print(username)