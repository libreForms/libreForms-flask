import os
import pandas as pd
import libreforms as form_src
from app.forms import parse_options, progagate_forms

def generate_csv_templates(form=None):
    if not os.path.exists ('static/tmp'):
        os.mkdir('static/tmp')
    if form:
        if parse_options(form=form)['_allow_csv_templates']:
            df = pd.DataFrame (headers=[x for x in progagate_forms(form).keys()])
            df.to_csv(f'static/tmp/{form.lower()}.csv', index=False)
    
    else:
        pass

def handle_csv_upload(csv_path, form=None):
    pass

if __name__=="__main__":
    for form in form_src.forms.keys():
        generate_csv_templates(form)