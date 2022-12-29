import datetime, os, json
import pandas as pd
from app import mongo
from markupsafe import Markup
from app.config import config
from app.models import db, User

def ____(requesting_user):
    with db.engine.connect() as conn:
        # email_list = db.select(User.__tablename__).where(User.__tablename__.columns.group == group)
        # filter(model.Email == EmailInput)
        email = db.session.query(User).filter_by(user=requesting_user.supervisor).first().email
        # print([x.email for x in email_list])
        return email

# here we return a slice of a collection based on the 
def _lookup_request_forms(collection=None, columns=[]):
    try:
        mongodb = mongo.MongoDB(
            user=config['mongodb_user'], 
            host=config['mongodb_host'], 
            port=config['mongodb_port'], 
            dbpw=config['mongodb_pw'])

        df = pd.DataFrame(list(mongodb.read_documents_from_collection(collection)))
        
        # if len(df.index < 1):
        #     return pd.DataFrame(columns=['combine']+[args])

        df2 = df[[x for x in columns]]

        # turn off warnings to avoid a rather silly one being dropped in the terminal,
        # see https://stackoverflow.com/a/20627316/13301284. 
        pd.options.mode.chained_assignment = None
        df2['combined'] = df2.apply(lambda row: ', '.join(row.values.astype(str)), axis=1)

        # print(df2)

        return df2
    except Exception as e:
        print ('error: ', e)
        return pd.DataFrame({'combined':['  ,']})

# def _db_lookup(collection, *args, combine=False):
#     try:
#         df = pd.DataFrame(list(mongodb.read_documents_from_collection(collection)))
#         new_df = pd.DataFrame()
#         if args:
#             for a in args:
#                 new_df[a] = df[a]
#             if combine:
#                 new_df['combine'] = ""
#                 for a in args:
#                     new_df['combine'] = new_df['combine'] + df[a] + " "
#             return new_df
#         else:
#             return df
#     except:
#         df = pd.DataFrame(columns=[x for x in args])
#         df['combine'] = None
#         return df


def generate_fake_jobcodes(num:int):
    import random
    TEMP = []
    for t in range(0,num):
        TEMP.append(str(random.randint(100000,999999)))
    return TEMP


forms = {
    # "perstat": {
    #     "Unit": {
    #         "input_field": {"type": "select", "content": ["687", "980", "753", "826"]},
    #         "output_data": {"type": "str", "required": True, "validators": [], 'description': "Select your unit name",},
    #         # "_deny_groups": ['admin']
    #     },
    #     "Authorized":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter your authorized number of soldiers"},
    #     },
    #     "On_Hand":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter your on-hand number of soldiers"},
    #     },
    #     "Gains":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter your gained number of soldiers"},
    #     },
    #     "Replacements":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter your replacement number of soldiers"},
    #     },
    #     "Returned_to_Duty":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter your returned to duty number of soldiers"},
    #     },
    #     "Killed":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers killed"},
    #     },
    #     "Wounded":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers wounded"},
    #     },
    #     "Nonbattle_Loss":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers lost for non-battle reasons"},
    #     },
    #     "Missing":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers missing"},
    #     },
    #     "Deserters":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers deserted"},
    #     },
    #     "AWOL":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers AWOL"},
    #     },
    #     "Captured":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": True, "validators": [], 'description': "Enter the number of soldiers captured"},
    #     },
    #     "Narrative":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": True, "validators": [], 'description': "Please provide any narrative explanation needed"},
    #     },
    #     '_enable_universal_form_access':True,
    #     "_description": "The personnel status report (PERSTAT) collects information about the number of battle ready soldiers are available at \
    #         a unit-by-unit level to inform leadership on their combat effectiveness.",
    #     "_dashboard": { 
    #         "type": "line",  # scatter, bar, histogram, line
    #         "fields": {
    #             "x": "Timestamp",   
    #             "y": "On_Hand", 
    #             "color": "Unit"
    #         }
    #     },
    #     "_allow_repeat": False, 
    #     "_allow_uploads": True, 
    #     "_allow_csv_templates": True, 
    #     "_suppress_default_values": False,
    #     "_allow_anonymous_access": True,
    #     '_submission': {
    #         '_enable_universal_form_access': True,
    #         '_deny_read': ['default'],
    #         '_deny_write': ['admin', 'default'],
    #     },
    #     '_send_form_with_email_notification':True,
    #     '_routing_list': {
    #         'type': 'static_list',
    #         'target': ['signe@atreeus.com'],
    #         # 'type': 'groups',
    #         # 'target': ['admins'],
    #         # 'type': 'custom',
    #         # 'target': some_func_returning_email_list(),
    #     },
        
    # },
    # "sitrep": { 
    #     "Unit": {
    #         "input_field": {"type": "radio", "content": ["687", "980", "753", "826"]},
    #         "output_data": {"type": "str", "required": True, "validators": []},
    #     },
    #     "Present_Location":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Activity":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #         # "_deny_groups": ['admins']
    #     },
    #     "Effective":{
    #         "input_field": {"type": "number", "content": [0]},
    #         "output_data": {"type": "float", "required": False, "validators": []},
    #     },
    #     "Own_Disposition":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Situation":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Operations":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Intelligence":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Logistics":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Communications":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Personnel":{
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "_dashboard": False,
    #     "_allow_repeat": False, 
    #     "_allow_uploads": True, 
    #     "_allow_csv_templates": True, 
    #     "_suppress_default_values": False, 
    #     # "_deny_groups": ['admin']
    # },
    # "salute": {             
    #     "Reporting_Unit":{
    #         "input_field": {"type": "radio", "content": ["687", "980", "753", "826"]},
    #         "output_data": {"type": "str", "required": True, "validators": []},
    #     },
    #     "Strength": {
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Activity": {
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Location": {
    #         "input_field": {"type": "text", "content": ["NA"]}, # (longitude, latitude), # < this should be multiple text/float fields that resolve to a tuple 
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     }, 
    #     "Enemy_Unit": {
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Time": {
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "Equipment": {
    #         "input_field": {"type": "text", "content": ["NA"]},
    #         "output_data": {"type": "str", "required": False, "validators": []},
    #     },
    #     "_dashboard": False,
    #     "_allow_repeat": False, 
    #     "_allow_uploads": True, 
    #     "_allow_csv_templates": True, 
    #     "_suppress_default_values": False,     
    #     '_deny_groups': ['anonymous',],
    #     '_enable_universal_form_access':True,
    # },
    # "dispatch": {    
    #     "Unit":"NA",      
    #     "Reporter":"NA",               
    #     "Expected_Time_of_Return":"NA",      
    #     "Destination":"NA",         
    #     "Equipment":"NA",           
    #     "Registration_Number":"NA",    
    #     "Operator_Name_Grade":"NA",
    #     "Passengers_Name_Grade":["","",""], # <<< this should be multiple text fields that resolve to a list data type
    #     "Remarks":"NA",
    #     "allow_repeat":True,          
    # },
    # "inventory": {     
        # "Unit":"NA",      
        # "Reporter":"NA",               
        # "Item_Name":"NA",      
        # "Number_Assigned":0,         
        # "Number_Accounted For":0,           
        # "Remarks":"NA",    
        # "allow_repeat":True,          
    # },
    "b1": {
        # "Name": {
        #     "input_field": {"type": "text", "content": ["NA"]},
        #     "output_data": {"type": "str", "required": False, "validators": [], "description": "",},
        # },
        # "Date": {
        #     "input_field": {"type": "text", "content": ["NA"]},
        #     "output_data": {"type": "str", "required": False, "validators": [], "description": "",},
        # },
        # "Confirmation": {
        #     "input_field": {"type": "text", "content": ["NA"]},
        #     "output_data": {"type": "str", "required": False, "validators": [], "description": "",},
        # },
        "Program": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Enter the Program/Tech Tree that this falls under",},
        },
        "Project": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "You may enter the Project that this falls under",},
        },
        "Item": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Enter the name of the item you would like to purchase",},
        },
        "Link": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Provide a link to the item you would like to purchase",},
        },
        "Comments": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Enter any additional comments you have",},
        },
        "Cost": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please use numbers and decimals only; no commas or currency symbols",},
        },
        "_dashboard": {             # defaults to False
            "type": "scatter",      # this is a highly powerful feature but requires
            "fields": {             # some knowledge of plotly dashboards; currently
                "x": "Timestamp",   # only line charts with limited features supported
                "y": "Int_Field",
                "color": "Text_Field"
            },
            # '_deny_groups': ['admin'],
        },
        "_description": "This form is for the purpose of requesting money to purchase equipment that one finds necessary for the program. This should be straightforward and easy to use. Additionally, the end result should be secure, with at least one identity check.",
        "_allow_repeat": False, # defaults to False
        "_allow_uploads": True, # defaults to False
        "_allow_csv_templates": True, # defaults to False
        "_suppress_default_values": False, # defaults to False
        # "_table":{'_deny_groups': ['admin'],},
    },
    "request": {
        # "Existing_Request": {
        #     "input_field": {"type": "autocomplete", "content": [r'{}'.format(x) for x in _db_lookup("perstat", "Reporter", "Timestamp", combine=True)['combine']]},
        #     "output_data": {"type": "str", "required": True, "validators": [], "description": "Select one of the available options",},
        # },
        # "Existing_Request":{
        #     "input_field": {"type": "radio", "content": ['Yes', 'No']},
        #     "output_data": {"type": "str", "required": True, "validators": [], "description": "Please identify whether you are modifying an existing request",},
        # },
        # "Existing_Jobcode":{
        #     "input_field": {"type": "autocomplete", "content": generate_fake_jobcodes(100)},
        #     "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select the existing jobcode for this request",},
        #     "_depends_on": ("Existing_Request", "Yes"),
        # },
        "Jobcode":{
            "input_field": {"type": "autocomplete", "content": generate_fake_jobcodes(100)},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select the jobcode for this request",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Shortname":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please print out the shortname for this jobcode",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Mission_Team":{
            "input_field": {"type": "checkbox", "content": ["Audit Policy and Quality Assurance (APQA)", "Applied Research and Methods (ARM)", "Chief Administrative Office (CAO)", "Contracting and National Security Acquisitions (CNSA)", "Continuous Process Improvement (CPI)", "Congressional Relations (CR)", "Defense Capabilities and Management (DCM)", "Forensic Audits and Investigative Service (FAIS)", "Financial Management and Assurance (FMA)", "Financial Management and Business Operations (FMBO)", "Financial Markets and Community Investment (FMCI)", "Field Operations (FO)", "Health Care (HC)", "Human Capital Office (HCO)", "Homeland Security and Justice (HSJ)", "International Affairs and Trade (IAT)", "Infrastructure Operations (IO)", "Information Technology and Cybersecurity (ITC)", "Learning Center (LC)", "Natural Resources and Environment (NRE)", "Office of the General Counsel (OGC)", "Office of the Inspector General (OIG)", "Office of Public Affairs (OPA)", "Professional Development Program (PDP)", "Physical Infrastructure (PI)", "Science, Technology Assessment, & Analytics (STAA)", "Strategic Issues (SI)", "Strategic Planning and External Liaison (SPEL)"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select the mission team for this request",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Analyst-in-Charge":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide the AIC's name for this request, if known",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Assistant_Director":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide the AD's name for this request, if known",},
            "_depends_on": ("Existing_Request", "No"),
        },
        # "Owner":{
        #     "input_field": {"type": "select", "content": [], "lookup": "user_list",},
        #     "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select the owner for this request",},
        #     "_depends_on": ("Existing_Request", "No"),
        # },
        "Description":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide a description for this request",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Job_Start_Date":{
            "input_field": {"type": "date", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide an estimated start date for this engagement, if known",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Job_End_Date":{
            "input_field": {"type": "date", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide an estimated end date for this engagement, if known",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Date_Specialist_Needed":{
            "input_field": {"type": "date", "content": ['']},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please provide a desired start date for this request",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Risk_Level":{
            "input_field": {"type": "select", "content": ["low", "medium", "high"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please identify the risk level for this request",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "Specializations":{
            "input_field": {"type": "checkbox", "content": [
                'SAS', 
                'Python', 
                'R', 
                'Stata', 
                'Javascript', 
                'FPDS', 
                'Census', 
                'Surveys', 
                'Interviews',
                'DCIs',
                'Small group methods',
                'Basic data reliability',
                'Advanced data reliability',
                'Sampling/statistics',
                'Literature review',
                'Program verification',
                'Report referencing',
                'Other not mentioned (please explain in description)'
            ],},
            "output_data": {"type": "str", "required": True, "validators": [], 'description': 'Please select any specializations required for this request'},
        },
        "Completed":{
            "input_field": {"type": "hidden", "content": [0, 1]},
            "output_data": {"type": "int", "required": False, "validators": [], "description": "Please identify whether this request has been completed",},
            '_deny_groups':[],
            '_make_visible_in_edits':True,
            '_secondary_input_type': 'radio',
        },
        # "See_Current_Requests":{
        #     "input_field": {"type": "radio", "content": [r'{}'.format(x) for x in _db_lookup("request", "Jobcode", "Owner", "Timestamp", combine=True)['combine']]},
        #     "output_data": {"type": "str", "required": False, "validators": []},
        #     "_depends_on": ("Existing_Request", "No"),
        # },
        "_description": Markup("This allows staff to submit requests for specialist work."),
        "_dashboard": { 
            "type": "scatter",  # scatter, bar, histogram, line
            "fields": {
                "x": "Date_Specialist_Needed",   
                "y": "Shortname", 
                "color": "Risk_Level",
            }
        },
        "_allow_repeat": False, # defaults to False
        "_allow_uploads": True, # defaults to False
        "_allow_csv_templates": True, # defaults to False
        "_suppress_default_values": True, # defaults to False
        "_allow_anonymous_access": True,
        '_submission': {
            '_enable_universal_form_access': True,
            '_deny_read': [],
            '_deny_write': [],
        },
        '_send_form_with_email_notification':True,
        '_routing_list': {
            'type': None,
            'target': [],
            # 'type': 'static_list',
            # 'target': ['signebedi@gmail.com'],
            # 'type': 'groups',
            # 'target': ['admin'],
            # 'type': 'custom',
            # 'target': some_func_returning_email_list(),
        },
        '_suppress_default_values':True,
        "_digitally_sign":True,
        '_presubmit_msg': "Clicking submit will affix your digital signature to this form, which carries with it a certification that the information contained within is true and accurate to the best of your knowledge.",
        '_form_approval': {
            'type': 'user_field',
            'target': 'manager',
        },

    },


    "bid": {
        "Request":{
            "input_field": {"type": "select", "content": [r'{}'.format(x) for x in _lookup_request_forms(collection='request',columns=['Jobcode', 'Shortname', '_id'])['combined']]},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Select the request that you would like to bid on"},
        },
        "Comments": {
            "input_field": {"type": "text", "content": [""]},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Enter any additional comments you have",},
        },

        "_description": "This allows specialists to submit bids for on existing requests.",
        "_allow_repeat": False, # defaults to False
        "_allow_uploads": True, # defaults to False
        "_allow_csv_templates": False, # defaults to False
        "_suppress_default_values": False, # defaults to False
        "_allow_anonymous_access": False,
        '_submission': {
            '_enable_universal_form_access': True,
            '_deny_read': ['default'],
            '_deny_write': ['default'],
        },
        '_send_form_with_email_notification':True,
        # "_deny_groups": ['manager'],
        '_routing_list': {
            'type': 'static_list',
            'target': ['signe@atreeus.com'],
            # 'type': 'groups',
            # 'target': ['admins'],
            # 'type': 'custom',
            # 'target': some_func_returning_email_list(),
        },

    },

    # 'rubric': {
    #     "Participant Name":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide the name of the participant whose memo you are reviewing",},
    #     },
    #     # "Owner":{
    #     #     "input_field": {"type": "select", "content": [], "lookup": "user_list",},
    #     #     "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select the owner for this request",},
    #     #     "_depends_on": ("Existing_Request", "No"),
    #     # },
    #     "Description":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide a description of this review",},
    #     },
    #     "Date":{
    #         "input_field": {"type": "date", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please enter the date  this review completed on",},
    #     },
    #     "_description": Markup("Fill out this form to reflect the Sifting & Winnowing rubric. See an example <a href='https://docs.google.com/document/d/1VV-DbAh0hR1pr7OqQ_kAUoT9TznvQRxIiP1jCR9bK78/edit'>here</a>."),
    #     "_allow_repeat": False, # defaults to False
    #     "_allow_uploads": True, # defaults to False
    #     "_allow_csv_templates": True, # defaults to False
    #     "_suppress_default_values": False, # defaults to False
    #     "_allow_anonymous_access": False,
    #     '_submission': {
    #         '_enable_universal_form_access': True,
    #         '_deny_read': ['default'],
    #         '_deny_write': ['default'],
    #     },
    #     '_send_form_with_email_notification':True,
    #     '_routing_list': {
    #         'type': 'custom',
    #         'target': [x for x in ['sbedi@wisc.edu', 'signe@siftingwinnowing.com']],
    #     },
    # },
    # "access": {
    #     "Name":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide your name",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Email":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide your email",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Mission_Team":{
    #         "input_field": {"type": "checkbox", "content": ["Audit Policy and Quality Assurance (APQA)", "Applied Research and Methods (ARM)", "Chief Administrative Office (CAO)", "Contracting and National Security Acquisitions (CNSA)", "Continuous Process Improvement (CPI)", "Congressional Relations (CR)", "Defense Capabilities and Management (DCM)", "Forensic Audits and Investigative Service (FAIS)", "Financial Management and Assurance (FMA)", "Financial Management and Business Operations (FMBO)", "Financial Markets and Community Investment (FMCI)", "Field Operations (FO)", "Health Care (HC)", "Human Capital Office (HCO)", "Homeland Security and Justice (HSJ)", "International Affairs and Trade (IAT)", "Infrastructure Operations (IO)", "Information Technology and Cybersecurity (ITC)", "Learning Center (LC)", "Natural Resources and Environment (NRE)", "Office of the General Counsel (OGC)", "Office of the Inspector General (OIG)", "Office of Public Affairs (OPA)", "Professional Development Program (PDP)", "Physical Infrastructure (PI)", "Science, Technology Assessment, & Analytics (STAA)", "Strategic Issues (SI)", "Strategic Planning and External Liaison (SPEL)"]},
    #         "output_data": {"type": "str", "required": True, "validators": [], "description": "Please select your mission team",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Supervisor":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide your DPM's name",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Description":{
    #         "input_field": {"type": "text", "content": ['']},
    #         "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide a an explanation of the reasons access is needed",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Date_Access_Needed":{
    #         "input_field": {"type": "date", "content": ['']},
    #         "output_data": {"type": "str", "required": True, "validators": [], "description": "Please provide a date that the access is needed by",},
    #     },
    #     "Data_Sensitivity":{
    #         "input_field": {"type": "select", "content": ["low", "medium", "high"]},
    #         "output_data": {"type": "str", "required": True, "validators": [], "description": "Please identify the data sensitivity you will be working on",},
    #         "_depends_on": ("Existing_Request", "No"),
    #     },
    #     "Access_Needed":{
    #         "input_field": {"type": "checkbox", "content": [
    #             'data', 
    #             'dev', 
    #             'main', 
    #             'data-gc', 
    #             'dev-gc', 
    #             'main-gc', 
    #             'Atlassian', 
    #             'GoAnywhere', 
    #             'Other not mentioned (please explain in description)'
    #         ],},
    #         "output_data": {"type": "str", "required": True, "validators": [], 'description': 'Please select the resources you are requesting access to'},
    #     },
    #     "Completed":{
    #         "input_field": {"type": "hidden", "content": [0, 1]},
    #         "output_data": {"type": "int", "required": False, "validators": [], "description": "Please identify whether this request has been completed",},
    #         '_deny_groups':[],
    #         '_make_visible_in_edits':True,
    #         '_secondary_input_type': 'radio',
    #     },
    #     # "See_Current_Requests":{
    #     #     "input_field": {"type": "radio", "content": [r'{}'.format(x) for x in _db_lookup("request", "Jobcode", "Owner", "Timestamp", combine=True)['combine']]},
    #     #     "output_data": {"type": "str", "required": False, "validators": []},
    #     #     "_depends_on": ("Existing_Request", "No"),
    #     # },
    #     "_description": Markup("This allows staff to submit requests for system access."),
    #     "_allow_repeat": False, # defaults to False
    #     "_allow_uploads": True, # defaults to False
    #     "_allow_csv_templates": True, # defaults to False
    #     "_suppress_default_values": True, # defaults to False
    #     "_allow_anonymous_access": True,
    #     '_submission': {
    #         '_enable_universal_form_access': True,
    #         '_deny_read': [],
    #         '_deny_write': [],
    #     },
    #     '_send_form_with_email_notification':True,
    #     '_routing_list': {
    #         'type': None,
    #         'target': [],
    #         # 'type': 'static_list',
    #         # 'target': ['signebedi@gmail.com'],
    #         # 'type': 'groups',
    #         # 'target': ['admin'],
    #         # 'type': 'custom',
    #         # 'target': some_func_returning_email_list(),
    #     },
    #     '_suppress_default_values':True,
    # },

    'support': {
        "Name":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide your name",},
        },
        "Affected_Systems":{
            "input_field": {"type": "checkbox", "content": [
                'Bid System', 
                'Atlassian', 
                'GoAnywhere', 
                'Other not mentioned (please explain in description)'
            ],},
            "output_data": {"type": "str", "required": True, "validators": [], 'description': 'Please select the systems affected'},
        },
        "Description":{
            "input_field": {"type": "text", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please provide a description of the problem",},
        },
        "Date":{
            "input_field": {"type": "date", "content": ['']},
            "output_data": {"type": "str", "required": False, "validators": [], "description": "Please enter the date  this review completed on",},
        },
        "Severity":{
            "input_field": {"type": "select", "content": ["low", "medium", "high"]},
            "output_data": {"type": "str", "required": True, "validators": [], "description": "Please identify the severity of the issue",},
            "_depends_on": ("Existing_Request", "No"),
        },
        "_description": Markup("Please use this form to describe any technical issues you are experiencing and a support professional will reach out within 24 hours."),
        "_allow_repeat": False, # defaults to False
        "_allow_uploads": True, # defaults to False
        "_allow_csv_templates": False, # defaults to False
        "_suppress_default_values": False, # defaults to False
        "_allow_anonymous_access": False,
        '_submission': {
            '_enable_universal_form_access': True,
            '_deny_read': ['default'],
            '_deny_write': ['default'],
        },
        '_send_form_with_email_notification':True,
        '_routing_list': {
            'type': 'group',
            'target': ['admin'],
        },
    },


}


