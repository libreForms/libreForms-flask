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
