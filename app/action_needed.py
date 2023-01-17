""" 
action_needed.py: action-needed tooltips and badge notifications

This script works closely with app/submissions.py to calculate 
a user's set of tasks where action is needed (approval, etc.)
and then returns a value - or set of values - than can whether
to show a notification badge and, if so, what kind of badge.

For more information, see the discussion at the following link:
https://github.com/signebedi/libreForms/issues/147.

"""

__name__ = "app.action_needed"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import numpy as np
from app import config, current_user, mongodb
from app.views.submissions import aggregate_approval_count


# a high level function that we can pass a large number
# of unique int values as args, of which it then returns
# the sum. The point is to devolve the actual decisions
# about 'what values to include' as an implementation 
# detail - in the end, we can pass many values to this
# in order to generate a count of current notifications
# for the current user, see https://github.com/signebedi/libreForms/issues/147. 
def aggregate_notification_count(*args:int) -> int:
    return round( np.sum(args) )


# this is just a quick abstraction that allows us to keep 
# actions_needed.aggregate_notification_count() generalized but 
# also account for current_app requirements and implementation 
# details in a single callable function. In theory, as the number 
# of features that create notifications for this application 
# increase, we can include them in the list below.
def standardard_total_notifications() -> int:
    return aggregate_notification_count(
            len(aggregate_approval_count(select_on=getattr(current_user,config['visible_signature_field'])).index), mongodb=mongodb,
        )
