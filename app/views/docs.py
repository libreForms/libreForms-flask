""" 
docs.py: user documentation views


When admins want to give written instructions to users on how to use tools


"""

__name__ = "app.views.docs"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# general packages
from xhtml2pdf import pisa
import os

# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, abort
from flask_login import current_user, login_required
from markupsafe import Markup


# import custom packages from the current repository
from app import config, log, mongodb, db
from app.views.external import conditional_decorator
from app.views.forms import standard_view_kwargs

def load_docs():
    if os.path.exists('docs.html'):
        with open('docs.html', 'r') as file:
            return Markup(file.read())
    else:
        return config['docs_body']

def replace_img_links(html_snippet, use_actual_file_path=False):

    # lines = html_snippet.splitlines()
    # for i, line in enumerate(lines):
    #     if '<img' in line:
    #         src_index = line.index('src="') + 5
    #         end_index = line.index('"', src_index)
    #         img_filename = line[src_index:end_index]
    #         new_src = 'app/static/docs/'+img_filename if use_actual_file_path else url_for("docs.docs_img", filename=img_filename)
    #         lines[i] = line.replace(img_filename, new_src)
    # return '\n'.join(lines)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_snippet, 'html.parser')
    img_tags = soup.find_all('img')
    for img_tag in img_tags:
        img_filename = img_tag['src']
        img_tag['src'] = 'app/static/docs/'+img_filename if use_actual_file_path else url_for("docs.docs_img", filename=img_filename)
    return str(soup)


bp = Blueprint('docs', __name__, url_prefix='/docs')

@bp.route(f'/')
@conditional_decorator(login_required, config['require_login_for_docs'])
def docs_home():

    # Update the docs_body config. This line of code will ensure that, if app/static/docs/docs.html exists,
    # it will always read that file, no matter what you've written to `docs_body`. For more discussion,
    # see https://github.com/libreForms/libreForms-flask/issues/374.
    config['docs_body'] = load_docs()

    return render_template('docs/documentation.html.jinja', 
            name='Documentation',
            documentation = replace_img_links(config['docs_body']) if config['add_assets_to_user_docs'] else config['docs_body'],
            subtitle="Home",
            type="docs",
            **standard_view_kwargs(),
        ) 

@bp.route('/images/<filename>')
@conditional_decorator(login_required, config['require_login_for_docs'])
def docs_img(filename):
    if config['add_assets_to_user_docs']:
        return send_from_directory('static/docs', filename)
    return abort(404)

@bp.route(f'/download')
@conditional_decorator(login_required, config['require_login_for_docs'])
def docs_download():

    if not config['allow_docs_pdf_download']:
        return abort(404)

    # Update the docs_body config. This line of code will ensure that, if app/static/docs/docs.html exists,
    # it will always read that file, no matter what you've written to `docs_body`. For more discussion,
    # see https://github.com/libreForms/libreForms-flask/issues/374.
    config['docs_body'] = load_docs()

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:

        HTML = replace_img_links(config['docs_body'], use_actual_file_path=True) if config['add_assets_to_user_docs'] else config['docs_body']

        print(HTML)

        HTML = f'''
                <html>
                <head>
                    <style>
                        body, body * {{
                            font-family: "Arial";
                            font-size: {config['pdf_download_font_size']}pt;
                        }}
                    </style>
                </head>
                <body>
                ''' + HTML + '''
                </body>
                </html>
                '''

        filename = "docs.pdf"
        fp = os.path.join(tempfile_path, filename)
        # Convert the HTML string to a PDF file
        with open(fp, "wb") as output_file:
            pisa_status = pisa.CreatePDF(HTML, dest=output_file)

        if pisa_status.err:
            flash("An error occurred while generating the PDF.", "warning")
            return redirect(url_for("docs.docs_home"))

        # flash("PDF successfully generated.", "success")
        return send_from_directory(tempfile_path,
                                filename, as_attachment=True)


