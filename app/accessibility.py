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


