""" 
action_needed.py: action-needed tooltips and badge notifications

This script works closely with app/submissions.py to calculate 
a user's set of tasks where action is needed (approval, etc.)

https://github.com/signebedi/libreForms/issues/147

"""

__name__ = "app.action_needed"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import numpy as np

# a high level function that we can pass a large number
# of unique int values as args, of which it then returns
# the sum. The point is to devolve the actual decisions
# about 'what values to include' as an implementation 
# detail - in the end, we can pass many values to this
# in order to generate a count of current notifications
# for the current user, see https://github.com/signebedi/libreForms/issues/147. 
def aggregate_notification_count(*args:int) -> int:
    return round( np.sum(args) )
