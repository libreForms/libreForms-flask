""" 
docs.py: user documentation views


When admins want to give written instructions to users on how to use tools


"""

__name__ = "app.views.docs"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.7.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import current_user, login_required

# import custom packages from the current repository
from app import config, log, mongodb, db
from app.views.external import conditional_decorator
from app.views.forms import standard_view_kwargs


bp = Blueprint('docs', __name__, url_prefix='/docs')

@bp.route(f'/')
@conditional_decorator(login_required, config['require_login_for_docs'])
def docs_home():
    return render_template('docs/documentation.html.jinja', 
            name='Documentation',
            documentation = config['docs_body'],
            subtitle="Home",
            type="docs",
            **standard_view_kwargs(),
        ) 
