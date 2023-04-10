""" 
docs.py: user documentation views


When admins want to give written instructions to users on how to use tools


"""

__name__ = "app.views.docs"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# general packages
from xhtml2pdf import pisa
import os

# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, abort
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

@bp.route(f'/download')
@conditional_decorator(login_required, config['require_login_for_docs'])
def docs_download():

    if not config['allow_pdf_download']:
        return abort(404)

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:

        filename = "docs.pdf"
        fp = os.path.join(tempfile_path, filename)
        # Convert the HTML string to a PDF file
        with open(fp, "wb") as output_file:
            pisa_status = pisa.CreatePDF(config['docs_body'], dest=output_file)

        if pisa_status.err:
            flash("An error occurred while generating the PDF.", "warning")
            return redirect(url_for("docs.docs_home"))
        else:
            flash("PDF successfully generated.", "success")
            return send_from_directory(tempfile_path,
                                    filename, as_attachment=True)