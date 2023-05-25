""" 
cli.py: CLI commands for managing the web application


This script is initially described in the following github issue:
https://github.com/libreForms/libreForms-flask/issues/123.



"""

__name__ = "app.views.cli"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# general dependencies
import os, sys, re, datetime
from collections import OrderedDict

# import flask-related packages
from flask import Blueprint
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash, check_password_hash
import click

# libreforms dependencies
from app import log
from app.models import db, User, OldPassword
from app.views.auth import get_recent_old_passwords
from app.config import config
from app.certification import generate_symmetric_key

def parse_addl_fields_as_options(options_dict=config['user_registration_fields'].copy()):
    options = []
    for key, value in options_dict.items():
        default_value = value['default_value'] if 'default_value' in value else value['content'][0]
        option = click.option(f"--{key}", prompt=True, type=value['type'], default=default_value, help=f"{key}, select from {value['content']}")
        options.append(option)
    # return tuple(options)

    def decorator(func):
        for option in reversed(options):
            func = option(func)
        return func

    return decorator

# borrowed version callback from https://click.palletsprojects.com/en/7.x/options/#callbacks-and-eager-options
def print_version(ctx, param, value, version=__version__):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f'libreForms-flask CLI version {version}.')
    ctx.exit()



# the following two methods are specific to the `usermod` command belows, see 
# https://github.com/libreForms/libreForms-flask/issues/329
def usermod_prompt_if_true(ctx, param, value):
    if value:

        username = ctx.params['username']
        # query user database for user
        user = User.query.filter_by(username=str(username)).first()
        
        # return 2 if user doesn't exist
        if isinstance(user,type(None)):
            click.echo(f"Error: user {username} does not exist. You can create them by running `flask libreforms useradd {username}`.")
            sys.exit(2)

        if param.human_readable_name == 'password':
            new_value = click.prompt(param.human_readable_name, hide_input=True, confirmation_prompt=True)  
        else:
            new_value = click.prompt(param.human_readable_name, default=getattr(user,param.human_readable_name))
        return new_value
    else:
        return value


# this is a restatement of the parse_addl_fields_as_options function above, with the click options specified  
# for the `usermod` command, see https://github.com/libreForms/libreForms-flask/issues/329.

def usermod_parse_addl_fields_as_options(options_dict=config['user_registration_fields'].copy()):
    options = []
    for key, value in options_dict.items():
        default_value = value['default_value'] if 'default_value' in value else value['content'][0]
        option = click.option(f"--{key}", is_flag=True, callback=usermod_prompt_if_true)
        options.append(option)
    # return tuple(options)

    def decorator(func):
        for option in reversed(options):
            func = option(func)
        return func

    return decorator


bp = Blueprint('cli', __name__)



###########################################
## `run` run libreforms development server
###########################################

@bp.cli.command('run')
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
def run():
    """Run libreForms in development mode."""

    # here we configure touch reload and create the dotenv file if none
    # exists, see https://github.com/libreForms/libreForms-flask/issues/233.
    with open ('libreforms.env', 'a'): pass

    # we load add a restart log, which will be used to trigger reloads
    with open (os.path.join('log', "restart.log"), 'a'): pass

    os.system("flask --debug run --extra-files libreforms.env --extra-files log/restart.log")


###########################################
## `useradd` add a new user to the user table
###########################################

# added as part of the following github issue, this allows admins to create users 
# through the tty, see https://github.com/libreForms/libreForms-flask/issues/242.
@bp.cli.command('useradd')
@click.argument('username')
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.option('--email', prompt=True, help='email, open field')
@click.password_option()
@click.option('--organization', prompt=True, default=config['default_org'], help='organization, open field')
@click.option('--phone', prompt=True, help='phone, open field')
@parse_addl_fields_as_options()
@click.option('--active', show_default=True, default=0, help='activate, options [0,1]')
@click.option('--theme', show_default=True, default=f'{"dark" if config["dark_mode"] else "light"}', help='theme, select from ["light","dark"].')
@click.option('--group', show_default=True, default=config['default_group'], help=f'group, select from {config["groups"]}.')
@with_appcontext
def create_user(username, email, password, organization, phone, active, theme, group, **kwargs):
# def create_user(**kwargs):
    """Add USERNAME to the libreforms user table."""

    # created_date = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    if phone == "":
        phone = None
    
    if email == "":
        email = None

    if organization == "":
        email = None

    error = None

    if not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'
    # added these per https://github.com/signebedi/libreForms/issues/122
    # to give the freedom to set these as required fields
    elif config['registration_email_required'] and not email:
        error = 'Email is required.'
    elif config['registration_phone_required'] and not phone:
        error = 'Phone is required.'
    elif config['registration_organization_required'] and not organization:
        error = 'Organization is required.'
    elif not re.fullmatch(r"^\w\w\w\w+$", username) or len(username) > 36:
        error = 'username does not formatting standards, length 4 - 36 characters, alphanumeric and underscore characters only.'
    elif email and not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
        error = 'Invalid email.' 
    elif phone and not re.fullmatch(r'^[a-z0-9]{3}-[a-z0-9]{3}-[a-z0-9]{4}$', phone):
        error = 'Invalid phone number (xxx-xxx-xxxx).' 
    elif email and User.query.filter_by(email=email).first():
        error = 'Email is already registered.' 
    elif User.query.filter_by(username=username.lower()).first():
        error = f'Username {username.lower()} is already registered.' 

    if error:
        click.echo(f"Failed: {error}")
        sys.exit(2)

    new_user = User(
        email=email, 
        username=username.lower(), 
        password=generate_password_hash(password, method='sha256'),
        organization=organization,
        group=config['default_group'],
        certificate=generate_symmetric_key(),
        phone=phone,
        theme='dark' if config['dark_mode'] else 'light', # we default to the application default
        # created_date=created_date,
        active=0 if config["enable_email_verification"] else 1,
        **kwargs, # https://stackoverflow.com/a/5710402
    ) 
    db.session.add(new_user)
    db.session.commit()
    click.echo(f"Success: created user {username}.")
    log.info(f"LIBREFORMS - successfully created user {username} via CLI.")
    sys.exit(0)


##############################################
## `usermod` modify a record in the user table
##############################################

# with the usermod command, we don't want to force admins to reiterate ALL of the user fields that they may need to
@bp.cli.command('usermod')
@click.argument('username', is_eager=True, required=False) # we set this as eager so the username is passed to the callback functions later
@click.option('--organization', is_flag=True, callback=usermod_prompt_if_true)
@click.option('--password', is_flag=True, callback=usermod_prompt_if_true)
@click.option('--phone', is_flag=True, callback=usermod_prompt_if_true)
@click.option('--theme', is_flag=True, callback=usermod_prompt_if_true)
@click.option('--group', is_flag=True, callback=usermod_prompt_if_true)
@usermod_parse_addl_fields_as_options()
@with_appcontext
# def modify_user(username, password, organization, phone, theme, group, **kwargs):
def modify_user(username=None, **kwargs):
    """Modify record for USERNAME in the libreforms user table."""

    if not username:
        click.echo(f"Error: please provide a USERNAME to modify.")
        sys.exit(2)

    # query user database for user
    user = User.query.filter_by(username=str(username)).first()
    
    # return 2 if user doesn't exist
    if isinstance(user,type(None)):
        click.echo(f"Error: user {username} does not exist. You can create them by running `flask libreforms useradd {username}`.")
        sys.exit(2)

    # quit if no arguments have been passed
    # print(len([x for x,y in kwargs.items() if y]))
    if len([x for x,y in kwargs.items() if y]) < 1:
        click.echo(f"Error: no arguments passed.")
        sys.exit(2)

    for attribute,value in kwargs.items():

        # we ignore attributes that have not been set here
        if not value:
            continue

        
        if attribute == 'password':
            # validate that password is not being reused
            old_passwords = get_recent_old_passwords(user, days=True)
            if any(check_password_hash(old_password.password, value) for old_password in old_passwords):
                click.echo(f"Error: The new password is the same as one of the user's old passwords. Please choose a different password.")
                log.warning(f"LIBREFORMS - failed to modify user {username} password via CLI: new password matches an old password.")
                sys.exit(2)

            # Save the old password to the OldPassword table before updating the user's password
            old_password_entry = OldPassword(user_id=user.id, password=user.password, timestamp=datetime.datetime.utcnow())
            db.session.add(old_password_entry)
            user.last_password_change = datetime.datetime.utcnow()

            # here we hash the password field, if it has been passed
            value = generate_password_hash(value, method='sha256')

        setattr(user, attribute, value)

    db.session.commit()

    #### add user modification logic

    click.echo(f"Success: modified user {username}. Run `flask libreforms id {username}` to see their new details.")
    log.info(f"LIBREFORMS - successfully modified user {username} via CLI.")
    sys.exit(0)


###############################
## `id` get user information
###############################

# this subcommand seeks to replicate the fuctionality of the unix `id` command.
# see discussion at https://github.com/libreForms/libreForms-flask/issues/332.
@bp.cli.command('id')
@click.argument('username') 
@with_appcontext
def id_user(username):

    # query user database for user
    user = User.query.filter_by(username=str(username)).first()

    # return 2 if user doesn't exist
    if isinstance(user,type(None)):
        click.echo(f"Error: user {username} does not exist. You can create them by running `flask libreforms useradd {username}`.")
        sys.exit(2)

    # create a string with the relevant user data (minus the user's password and certificate)
    # s = '\n'.join([f"{x}: {getattr(user,x)}" for x in dir(user) if not x.startswith('_') and x not in ['password', 'certificate']])
    s = '\n'.join([f"{x}: {getattr(user,x)}" for x in ['username','email', 'organization','group','phone','theme','created_date','active',]+[x for x in config['user_registration_fields'].keys()]])

    click.echo(s)
    sys.exit(0)



##############################################
## `activate` manage user activation status
##############################################

@bp.cli.command('activate')
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
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




########################################################################
## `generate-accessibility-audio` generate audio files for accessibility
########################################################################

# this command is used to generate accessibility audio for the libreForms-flask web application,
# see https://github.com/libreForms/libreForms-flask/issues/286 for more information.
@bp.cli.command('generate-accessibility-audio')
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
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
