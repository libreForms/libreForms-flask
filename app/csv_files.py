""" 
csv_files.py: implementation of temp filesystem

### THIS SHOULD PROBABLY HAVE ITS NAME CHANGED
### TO TMP_FILESYSTEMS.PY TO REFLECT WHAT IT
### ACTUALLY DOES. 



"""

__name__ = "app.csv_files"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.2"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, tempfile
import pandas as pd
import libreforms
# from .forms import parse_options, progagate_forms


def tempfile_init_tmp_fs():
    temp_folder = tempfile.mkdtemp()
    return temp_folder

## deprecated in favor of tempfile_init_tmp_fs()
def init_tmp_fs(delete_first=False):
    if delete_first:
# if application tmp/ path doesn't exist, make it
        if os.path.exists ("app/static/tmp/"):
            os.system("rm -rf app/static/tmp/")
        os.mkdir('app/static/tmp/')
    else:
        if not os.path.exists ("app/static/tmp/"):
            os.mkdir('app/static/tmp/')    

## deprecated by new approach to file downloads
# def generate_csv_templates(form=None):
#     if form:
#         if parse_options(form=form)['_allow_csv_templates']:

#             # this is our first stab at building templates, without accounting for nesting or repetition
#             df = pd.DataFrame (columns=[x for x in progagate_forms(form).keys()])
#             # placeholder for nesting
#             # placeholder for repetition
#             df.to_csv(f'app/static/tmp/{form.lower().replace(" ","")}.csv', index=False)
#     # IF NO option is passed for 'form', we will just generate them ourselves... this is the default behavior
#     else:
#         for form in libreforms.forms.keys():
#             if parse_options(form=form)['_allow_csv_templates']:

#                 # this is our first stab at building templates, without accounting for nesting or repetition
#                 df = pd.DataFrame (columns=[x for x in progagate_forms(form).keys()])
#                 # placeholder for nesting
#                 # placeholder for repetition
#                 df.to_csv(f'app/static/tmp/{form.lower().replace(" ","")}.csv', index=False)


def handle_csv_upload(csv_path, form=None):
    pass