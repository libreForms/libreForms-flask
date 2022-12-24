""" 
tmpfiles.py: implementation of temp filesystem



"""

__name__ = "app.tmpfiles"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
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


def handle_csv_upload(csv_path, form=None):
    pass