import os
import pandas as pd
import libreforms
# from .forms import parse_options, progagate_forms

def init_tmp_fs(delete_first=False):
    if delete_first:
# if application tmp/ path doesn't exist, make it
        if os.path.exists ("app/static/tmp/"):
            os.system("rm -rf app/static/tmp/")
        os.mkdir('app/static/tmp/')
    else:
        if not os.path.exists ("app/static/tmp/"):
            os.mkdir('app/static/tmp/')    

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