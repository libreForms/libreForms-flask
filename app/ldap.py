""" 
ldap.py: ldap auth integration



"""

__name__ = "app.ldap"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import ldap

class initLDAP():
    def __init__(self, server=None, port=None):
        try:
            self.l =  ldap.initialize(f'ldaps://{server}')
            self.l.set_option(ldap.OPT_REFERRALS, 0)
        except:
            return "Error connecting to LDAP server"

    def connect(self, username=None, password=None, connection_string=None):
        try:
            self.l.simple_bind_s("uid={username},{connection_string}", password)
        except:
            return "Error authenticating user"
