
"""
filters.py: convert text to conditions without eval()

References:
1. https://github.com/libreForms/libreForms-flask/issues/204 (comparison operators)
2. https://github.com/libreForms/libreForms-flask/issues/213 (identity & membership operators)

"""

__name__ = "app.filters"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"




# these are the operators supported in text
def get_operators():
    return {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>=': lambda a, b: a >= b,
    }


# this function takes a string, and processes it into 
# filters / conditions
def preprocess_text_filters(string):
    return True



def validate_filters():
    return True


def lint_filters(string):
    return True