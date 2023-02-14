"""
accessibility.py: accessibility-related functions for the application front-end

One approach to accessibility is through TTS audio support when completing forms.
We've documented this line of effort in a number of issues, but the first is:
https://github.com/libreForms/libreForms-flask/issues/283. There are a handful of 
ways to handle TTS - but the two obvious approaches are realtime TTS, which is 
flexible but not performant, and pre-rendered audio, which incurs a lot of resource
costs at app startup to generate the audio files and store them in a temporary file 
system. To avoid this, we may be able to enable a CLI command to generate and 
regenerate these files, to avoid the high startup costs.

In addition we are using gTTS for TTS initially but may change this in the future, see
https://github.com/libreForms/libreForms-flask/issues/284.

"""

__name__ = "app.accessibility"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.5.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


######################
# Audio Accessibility
######################

from gtts import gTTS
import os


def generate_audio_file(base_string, destination_filepath, language='en'):

    # generate the audio
    myobj = gTTS(text=base_string, lang=language, slow=False)

    # and save it to the designated destination ... 
    # ideally, to a tmpfile defined in app.tmpfiles
    myobj.save(destination_filepath)


def generate_all_app_audio_files(directory):
    from libreforms import forms

    for form,data in forms.items():

        # we add a contextualizing string that is included at the begining 
        # of the audio to give the user an idea of the form they are completing.
        form_prep_str = f"This is the {form.replace('_',' ')} form. "

        if '_description' in data:
            generate_audio_file(base_string=form_prep_str+data['_description'], destination_filepath=os.path.join(directory,f'{form}__description.mp3'))
            print(form_prep_str+data['_description'])

        if '_presubmit_msg' in data:
            generate_audio_file(base_string=form_prep_str+data['_presubmit_msg'], destination_filepath=os.path.join(directory,f'{form}__presubmit_msg.mp3'))
            print(form_prep_str+data['_presubmit_msg'])

        for field,field_config in data.items():

            # if the field starts with the reserved character, 
            # we ignore it 
            if field.startswith('_'):
                continue
            
            if 'description' in field_config['output_data']:

                # we add a contextualizing string that is included at the begining 
                # of the audio to give the user an idea of the field they are completing.    
                field_prep_str = f"This is the {field.replace('_',' ')} field of the {form.replace('_',' ')} form. It is a{' required' if 'required' in field_config['output_data'] and field_config['output_data']['required'] else ''} {field_config['input_field']['type']} field. "
                print(field_prep_str+field_config['output_data']['description'])
                generate_audio_file(base_string=field_prep_str+field_config['output_data']['description'], destination_filepath=os.path.join(directory,f'{form}_{field}.mp3')) 


