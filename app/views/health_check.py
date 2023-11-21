""" 
health_check.py: health checks for the libreForms app

Health checks can be useful methods to verify that the application is 
working as expected. Here, we implement two health checks: alive and 
ready; these are based on the liveness and readiness checks used in k8s:
https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
And borrowed somewhat from the flask-healthz, see https://pypi.org/project/flask-healthz/.
For further discussion, see https://github.com/signebedi/libreForms/issues/171.

"""

__name__ = "app.views.health_check"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"



from flask import Blueprint, Response
import json

# import custom packages from the current repository
from app import log, config, mongodb
from app.models import User, db


def validate_condition(condition, success=config['success_code'], error=config['error_code']):
    try:
        assert (condition)
        return success
    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return error


def formulate_health_check_response(code, status):
    return Response(json.dumps({'status':status}), status=code, mimetype='application/json')



bp = Blueprint('health_check', __name__, url_prefix='/health')

if config['enable_health_checks']:

    # here we add the alive route, which will return 200 if the site 
    # can be reached and, if a custom alive condition has been added, 
    # this check must also pass. If these checks fail, we return a 503 
    # error based on the discussion here https://stackoverflow.com/a/48005358/13301284.
    @bp.route('/alive')
    def alive():
        check = validate_condition(config['alive_condition'])
        if check == config['success_code']:
            return formulate_health_check_response (config['success_code'], 'alive')
        
        else:
            return formulate_health_check_response (config['error_code'], 'failed') 



    # here we add the alive route, which check if a custom rrady condition
    # has been set in the form config and, if not, default to checking the 
    # SQL and MongoDB database connections. If these checks fail, we return
    # a 503 error based on the discussion here https://stackoverflow.com/a/48005358/13301284.
    @bp.route('/ready')
    def ready():

        # has a custom ready condition been set and, if so, has the check passed?
        if config['ready_condition']:
            check = validate_condition(config['ready_condition'])
            # print('ready_condition', check)

            if check == config['success_code']:
                return formulate_health_check_response (config['success_code'], 'ready')
            
            else:
                return formulate_health_check_response (config['error_code'], 'failed') 


        # if no custom ready condition has been set, fall back on checking the 
        # SQL and mongodb connection 
        else:
            # first we validate the mongodb connection
            check = validate_condition(mongodb.check_connection())
            # print('mongodb', check)

            # if it passes...
            if check == config['success_code']:

                # then we check if the user database has at least one value, and return a success if it passes
                check = validate_condition(db.session.query(User).filter_by(username='libreforms').count() > 0)
                # print('sqlalchemy', check)
 
                if check == config['success_code']:
                    return formulate_health_check_response (config['success_code'], 'ready')
                
                else:
                    return formulate_health_check_response (config['error_code'], 'failed') 

            else:
                return formulate_health_check_response (config['error_code'], 'failed') 
