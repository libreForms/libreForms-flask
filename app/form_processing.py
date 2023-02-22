"""
form_processing.py: triggers for form behavior after submission

After forms are submitted, they are stored by default in a MongoDB
collection named after the form's name. For example, a user submits
`form_a`, and the document details are written to a MongoDB database
named `libreforms` under the `form_a` collection. But what if you
want to define complex form behavior after submission? That is what
form_processing is intended to solve, by defining a set of triggers
that take a list of functions as its args. This I think is best 
instantiated as a class, which persists for the duration of an app 
runtime. For example, we instantiate postProcessor in app/__init__.py,
which stores the form config data, and other relevant data, and then 
we call it from within the app context when a trigger criteria is met.
See https://github.com/libreForms/libreForms-flask/issues/201.

These triggers are:

    onCreation - only when the form is first created
    onSubmission - when the form is created, and all subsequent changes
    onUpdate - only when the form is updated, not when first created
    onApproval - when the form is approved
    onDisapproval - when the form is disapproved


"""

__name__ = "app.form_processing"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.5.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


class postProcessor:
    def __init__(self, forms=None):

        # import the forms object if none is passed
        if not forms:
            from libreforms import forms

        # store the forms object as a class attribute 
        self.forms = forms

    def onCreation (self, *args):
        pass
    def onSubmission (self, *args):
        pass
    def onUpdate (self, *args):
        pass
    def onApproval (self, *args):
        pass
    def onDisapproval (self, *args):
        pass
