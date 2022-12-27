""" 
tmpfiles.py: implementation of temp filesystem

For a number of reasons, the web application needs to read 
and write to a temporary filesystem to manage document 
uploads and downloads. This script contains the methods
needed to do so.

# init_tmp()

It took awhile for us to get to this approach, which
to this day seems like the easiest way to initialize a 
temporary filesystem, and deprecate the previous method,
which is still included below, called init_tmp_fs().
One of the major advantages of this approach is that it 
just creates a temporary folder in /tmp and logs the name.

"""

__name__ = "app.tmpfiles"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os 
import tempfile
import contextlib
import shutil

# borrowed from https://stackoverflow.com/a/21922442/13301284
# to enable context management when using temp directories, see
# https://github.com/signebedi/libreForms/issues/169
@contextlib.contextmanager
def temporary_directory(*args, **kwargs):
    d = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield d
    finally:
        shutil.rmtree(d)


def init_tmp():
    temp_folder = tempfile.mkdtemp()
    return temp_folder

## deprecated in favor of init_tmp()
def init_tmp_fs(delete_first=False):
    if delete_first:
# if application tmp/ path doesn't exist, make it
        if os.path.exists ("app/static/tmp/"):
            os.system("rm -rf app/static/tmp/")
        os.mkdir('app/static/tmp/')
    else:
        if not os.path.exists ("app/static/tmp/"):
            os.mkdir('app/static/tmp/')    


#  deprecated: this will be handled in the application code
# # process a csv upload, with add'l options to treat 
# # the file as safe (defaults to unsafe)
# def handle_csv_upload(csv_path, form=None, safe=False):
#     pass