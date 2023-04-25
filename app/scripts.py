""" 
scripts.py: additional context-free scripts


"""

__name__ = "app.scripts"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


def convert_to_string(data):
    if isinstance(data, list):
        # Convert each item in the list to a string and join them with commas
        return ", ".join(str(item) for item in data)
    elif isinstance(data, dict):
        # Convert each key-value pair in the dictionary to a string and join them with commas
        return ", ".join(f"{key}: {value}" for key, value in data.items())
    # Return the input as a string
    return str(data)


def prettify_time_diff(time:float):
    if time < 3600:
        if (time / 60) < 1:
            return "less than a minute ago"
        elif (time / 90) < 1 <= (time / 60):
            return "about a minute ago"
        elif (time / 420) < 1 <= (time / 90):
            return "a few minutes ago"
        elif (time / 900) < 1 <= (time / 420):
            return "about ten minutes ago"
        elif (time / 1500) < 1 <= (time / 900):
            return "about twenty minutes ago"
        elif (time / 2100) < 1 <= (time / 1500):
            return "about thirty minutes ago"
        elif (time / 2700) < 1 <= (time / 2100):
            return "about thirty minutes ago"
        elif (time / 3300) < 1 <= (time / 2700):
            return "about forty minutes ago"
        elif (time / 3600) < 1 <= (time / 3300):
            return "about fifty minutes ago"
    elif 7200 > time >= 3600: 
        return f"about an hour ago"
    elif 84600 > time >= 7200: # we short 86400 seconds by 1800 seconds to manage rounding issues
        return f"about {round(time / 3600)} hours ago"
    elif 84600 <= time <= 171000: # we short 172800 seconds by 1800 seconds to manage rounding issues
        return f"about a day ago"
    elif 171000 <= time: # we short 172800 seconds by 1800 seconds to manage rounding issues
        return f"about {round(time / 86400)} days ago"
    else:
        return ""


# here we add a mask function that we can use to obfuscate a potentially sensitive string, 
# like a signing key, see https://github.com/libreForms/libreForms-flask/issues/384.
def mask_string(string, show_chars:int=4, obfsc_char='*', override=False):
    if len(string) > show_chars and not override:
        return obfsc_char * (len(string)-show_chars) + string[-show_chars:]
    return string


