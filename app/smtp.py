""" 
smtp.py: implementation of SMTP mail logic

This script creates a Mailer class to store the smtp server credentials 
in memory, and then allows us to send mail using the send_mail method.



# Routing lists

The libreForms configuration allows administrators to define routing lists for
each form. These routing lists are used to notify various groups when a form has 
been submitted or changed, see https://github.com/signebedi/libreForms/issues/94.
This is closely tied to, but not entirely analogous with, the form approval process,
see https://github.com/signebedi/libreForms/issues/8. 

In this script, the `send_mail` method accepts an optional list `cc_address_list`,
which expects a list of emails to carbon copy on an outgoing email. This can be
more broadly used than just routing lists, however. 

To see the logic that implements the routing list, see the `rationalize_routing_list`
method in app.views.forms.


# send_mail() method

This is the primary method of the Mailer class; it's used to send outgoing mail
using smtplib. It creates a connection with the mail server each time mail is sent.

It is implemented synchronously; however, there is a celery wrapper that is disabled 
by default to send mail asynchronously, see config.send_mail_asynchronously for the 
configuration. The asynchronous method is named `send_mail_async` and defined in 
app/__init__.py.


"""

__name__ = "app.smtp"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.8.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import ssl
import smtplib 
import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

class Mailer():
    def __init__(self, mail_server=None, port=None, 
                        username=None, password=None, 
                        from_address=None, enabled=True):

        if enabled:
            # setting up ssl context
            self.context = ssl.create_default_context()
            self.mail_server = mail_server
            self.port = port
            self.username = username
            self.password = password
            self.from_address = from_address
            self.enabled = True
        else: 
            self.enabled = False

    # borrowed shamelessly from 
    # https://www.aabidsofi.com/posts/sending-emails-with-aws-ses-and-python/
    def send_mail(self, subject=None, content=None, to_address=None, cc_address_list=[], logfile=None):

        # only if we have enabled SMTP
        if self.enabled:
            try:
                # creating an unsecure smtp connection
                with smtplib.SMTP(self.mail_server,self.port) as server:

                    msg = MIMEMultipart()
                    msg['Subject'] = subject
                    msg['From'] = self.from_address
                    msg['To'] = to_address
                    # print(cc_address_list)
                    msg['Cc'] = ", ".join(cc_address_list) if cc_address_list and len(cc_address_list)>0 else None

                    msg.attach(MIMEText(content))

                    # securing using tls
                    server.starttls(context=self.context)

                    # authenticating with the server to prove our identity
                    server.login(self.username, self.password)

                    # sending a plain text email
                    server.sendmail(self.from_address, [to_address]+cc_address_list, msg.as_string())
                    # server.send_message(msg.as_string())

                    if logfile: logfile.info(f'successfully sent an email to {to_address}')
                    
                    return True

            except Exception as e: 
                if logfile: logfile.error(f'could not send an email to {to_address} - {e}')
                
                return False
