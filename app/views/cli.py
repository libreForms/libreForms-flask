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
import click, os, sys

bp = Blueprint('cli', __name__)

@bp.cli.command('useradd')
@click.argument('username')
@with_appcontext
def create_user(username):
    """Add USERNAME to the libreforms user db."""
    click.echo(username)


@bp.cli.command('activate')
@click.argument('username')
@click.option('--deactivate', is_flag=True, show_default=True, default=False, help='deactivate USERNAME')
@with_appcontext
def activate_user(username):
    """Manage active status for USERNAME in libreforms user db."""
    click.echo(username)


# this command is used to generate accessibility audio for the libreForms-flask web application,
# see https://github.com/libreForms/libreForms-flask/issues/286 for more information.
@bp.cli.command('generate-accessibility-audio')
@click.option('--directory', show_default=True, default='/opt/libreForms/app/static', help='directory to store accessibility audio')
@with_appcontext
def activate_user(directory):
    """Generate accessibility audio for libreForms web app."""
    
    # first we ensure a valid path has been provided
    if not os.path.isdir(directory):
        click.echo (f"{directory} is not a valid path.")
        sys.exit(2)

    # here we generate the audio, provide messages to the user, and exit 0 on success
    from app.accessibility import generate_all_app_audio_files
    click.echo(f"Started generating accessibility audio in {directory}.")
    generate_all_app_audio_files(directory)
    click.echo (f"Successfully generated accessibility audio in {directory}.")
    sys.exit(0)
