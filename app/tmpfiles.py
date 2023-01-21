""" 
tmpfiles.py: implementation of temp filesystem

For a number of reasons, the web application needs to read 
and write to a temporary filesystem to manage document 
uploads and downloads. This script contains the methods
needed to do so.

# temporary_directory()

This approach allows us to use context management to create
temp directories for a purpose, then delete them immediately
after so to avoid sprawl in unused temp directories. This
does a little garbage collection for us, in cases where
we have no reason to allow the filesystem to persist 
beyond its immediate use. This approach was borrowed from
https://stackoverflow.com/a/21922442/13301284, and is discussed
further at https://github.com/signebedi/libreForms/issues/169.

There are two kinds of file storage needed: ephemeral and persistent. 
Ephemeral storage encapsulates when (a) the application is generating 
a temp file and needs a file path to temporarily store it at; (b) when 
an end user uploads some file (typically a CSV) to read into the 
application, but does not need to reuse. Persistent storage encapsulates 
attachments or file uploads that will need to be re-accessed; these should 
be stored in a separate, noexec filesystem with antivirus scanning 
(like ClamAV).

# init_tmp()

It took awhile for us to get to this approach, which
to this day seems like the easiest way to initialize a 
temporary filesystem that doesn't need to be context-
bound, and deprecated the previous method, which is 
still included below, called init_tmp_fs(), as it includes
a numer of potentially useful tidbits that we may reuse.
One of the major advantages of this approach is that it 
just creates a temporary folder in /tmp and returns the name.
This approach, however, was generally deprecated in favor of
the context-bound temporary_directory() approach, see above.

"""

__name__ = "app.tmpfiles"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os 
import tempfile
import contextlib
import shutil

# borrowed from https://stackoverflow.com/a/21922442/13301284
# to enable context management when using temp directories, see
# https://github.com/signebedi/libreForms/issues/169.
@contextlib.contextmanager
def temporary_directory(*args, **kwargs):
    d = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield d
    finally:
        shutil.rmtree(d)

# deprecated in favor of context-bound temporary_directory(), but keeping
# in place in case there is a use case for a persistent temp directory. 
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