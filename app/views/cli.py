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


# general dependencies
import os, sys

# import flask-related packages
from flask import Blueprint
from flask.cli import with_appcontext
import click

# libreforms dependencies
from app import log
from app.models import db, User
from app.config import config

bp = Blueprint('cli', __name__)

# @bp.cli.command('test')
# @click.option('--prompt', prompt=True, help='this option will prompt for a response if none is given.')
# def test_command(prompt):
#     """This is a test command."""
#     click.echo(prompt)


# STILL NEED TO ADD ADD'L ADMIN-DEFINED OPTIONS
@bp.cli.command('useradd')
@click.argument('username')
@click.option('--email', prompt=True, help='email')
@click.password_option()
@click.option('--organization', prompt=True, default=config['default_org'], help='organization')
@click.option('--phone', prompt=True, help='phone')
@click.option('--active', show_default=True, default=0, help='activate, options [0,1]')
@click.option('--theme', show_default=True, default=f'{"dark" if config["dark_mode"] else "light"}', help='theme, select from ["light","dark"]')
@click.option('--group', show_default=True, default=config['default_group'], help=f'group, select from {config["groups"]}')
@with_appcontext
def create_user(username, email, password, organization, phone, active, theme, group):
    """Add USERNAME to the libreforms user db."""
    click.echo(f"{username}, {email}, {password}, {organization}, {phone}, {active}, {theme}, {group},")
    # click.echo("Need to add user options and interactive user creation process.")
    
    # id = db.Column(db.Integer, primary_key=True) 
    # certificate = db.Column(db.LargeBinary())
    # created_date = db.Column(db.String(1000))


@bp.cli.command('activate')
@click.option('--deactivate', is_flag=True, show_default=True, default=False, help='deactivate USERNAME')
@click.option('-s','--show', is_flag=True, show_default=True, default=False, help='show activation status for USERNAME')
@click.argument('username')
@with_appcontext
def activate_user(username,deactivate=False,show=False):
    """Manage active status for USERNAME in libreforms user db."""

    # query user database for user
    user = User.query.filter_by(username=str(username)).first()
    
    # return 2 if user doesn't exist
    if isinstance(user,type(None)):
        click.echo(f"Error: user {username} does not exist. You can create them by running `flask libreforms useradd {username}`.")
        sys.exit(2)
    
    if show:
        click.echo(f"Success: user {username} has an active status of {user.active}.")
        sys.exit(0)
       

    # return 2 if user is already inactive when deactivation is requested, or 
    # if user is already active when activation is requested.
    if (deactivate and user.active==0) or (not deactivate and user.active==1):
        click.echo(f"Error: user {username} is already {'inactive' if deactivate else 'active'}.")
        sys.exit(2)    

    user.active=0 if deactivate else 1 
    db.session.commit()
    click.echo(f"Success: {'deactivated' if deactivate else 'activated'} user {username}.")
    log.info(f"LIBREFORMS - successfully {'deactivated' if deactivate else 'activated'} user {username} via CLI.")
    sys.exit(0)


# this command is used to generate accessibility audio for the libreForms-flask web application,
# see https://github.com/libreForms/libreForms-flask/issues/286 for more information.
@bp.cli.command('generate-accessibility-audio')
@click.option('--directory', show_default=True, default='/opt/libreForms/app/static', help='directory to store accessibility audio')
@with_appcontext
def generate_accessibility_audio(directory):
    """Generate accessibility audio for libreForms web app."""
    
    # first we ensure a valid path has been provided
    if not os.path.isdir(directory):
        click.echo (f"{directory} is not a valid path.")
        sys.exit(2)

    # here we generate the audio, provide messages to the user, and exit 0 on success
    from app.accessibility import generate_all_app_audio_files
    click.echo(f"Started generating accessibility audio in {directory}.")
    generate_all_app_audio_files(directory)
    click.echo (f"Success: generated accessibility audio in {directory}.")
    sys.exit(0)
