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
    onDuplication - when the form is duplicated

Each of these should probably be tied to a separate trigger in the form 
config, like:

    _on_creation
    _on_submission
    _on_update
    _on_approval
    _on_disapproval
    _on_duplication

"""

__name__ = "app.form_processing"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app.views.forms import propagate_form_configs
# from libreforms import forms
from app.mongo import mongodb

class postProcessor:
    def __init__(self, form_data=None,db=None):

        # store the forms object as a class attribute 
        self.forms = form_data if form_data else propagate_form_configs

        # store the mongodb object as a class attribute 
        self.mongodb = db if db else mongodb

    def onCreation (self, document_id:str, form_name:str, *args, **kwargs):

        func_list = self.forms(form_name)['_on_creation']

        if len (func_list) > 0 and isinstance(func_list, list): 
            document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
            if not document:
                return None

            for function in func_list:
                function(document)

            return True
        else:
            return False


    # def onSubmission (self, document_id:str, form_name:str, *args, **kwargs):

    #     func_list = self.forms(form_name)['_on_submission']

    #     if len (func_list) > 0 and isinstance(func_list, list): 
    #         document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
    #         if not document:
    #             return None

    #         for function in func_list:
    #             function(document)

    #         return True
    #     else:
    #         return False



    def onUpdate (self, document_id:str, form_name:str, *args, **kwargs):

        func_list = self.forms(form_name)['_on_update']

        if len (func_list) > 0 and isinstance(func_list, list): 
            document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
            if not document:
                return None

            for function in func_list:
                function(document)

            return True
        else:
            return False


    def onApproval (self, document_id:str, form_name:str, *args, **kwargs):

        func_list = self.forms(form_name)['_on_approval']

        if len (func_list) > 0 and isinstance(func_list, list): 
            document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
            if not document:
                return None

            for function in func_list:
                function(document)

            return True
        else:
            return False


    def onDisapproval (self, document_id:str, form_name:str, *args, **kwargs):

        func_list = self.forms(form_name)['_on_disapproval']

        if len (func_list) > 0 and isinstance(func_list, list): 
            document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
            if not document:
                return None

            for function in func_list:
                function(document)

            return True
        else:
            return False

    # Added in https://github.com/libreForms/libreForms-flask/issues/465
    def onDuplication (self, document_id:str, form_name:str, *args, **kwargs):

        func_list = self.forms(form_name)['_on_duplication']

        if len (func_list) > 0 and isinstance(func_list, list): 
            document = self.mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
            
            if not document:
                return None

            for function in func_list:
                function(document)

            return True
        else:
            return False
