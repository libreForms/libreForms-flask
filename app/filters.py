
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


# these are the operators supported in text, borrowed shamelessly from
# https://stackoverflow.com/a/45151961/13301284. 
def get_operators():
    return {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        # 'in': lambda a, b: a in b,
    }


# this function takes a string, and processes it into 
# filters / conditions
def preprocess_text_filters(string):
    return [x.strip() for x in string.split(',')]


# here we actually assess the truthfulness of a set of 
# filters; this is the method that we should call when
# validating a string stored as a report's filters.
# Worried this is a little bit computationally expensive..
def validate_filters(s):

    STRINGS = preprocess_text_filters(s)

    for string in STRINGS:
        operand1, comparison, operand2 = string.split()
        COMPARISONS = get_operators()

        # if the attempted comparison isn't supported, then
        # we fail
        if comparison not in COMPARISONS:
            return False

        # if any of the conditions assess false, then return False
        if not COMPARISONS[comparison](operand1, operand2):
            return False
        
    # if the above passes, then return True
    return True


def lint_filters(s, *args, **kwargs):

    STRINGS = preprocess_text_filters(s)

    for string in STRINGS:
        try:
            operand1, comparison, operand2 = string.split()
        except:
            return False
        COMPARISONS = get_operators()

        if comparison not in COMPARISONS:
            return False

    return True


def dummy_test(STRINGS = ['my_city_name == my_city_name','6001 >= 6005', 'my_city_name == your_city_name', '13 != 14', '1 < 4', 'vary in [varynice,telluride]']):

    for string in STRINGS:
        operand1, comparison, operand2 = string.split()
        COMPARISONS = get_operators()
        if comparison in COMPARISONS:
                print(string, COMPARISONS[comparison](operand1, operand2))
        else:
                print(string, "Unknown comparison")
