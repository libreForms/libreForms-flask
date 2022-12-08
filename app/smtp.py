""" 
smtp.py: implementation of SMTP mail logic



# Routing lists



# sendMail() class




# send_mail() method





"""

__name__ = "app.smtp"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.2"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import ssl
import smtplib 
import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

class sendMail():
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
                    msg['Cc'] = ", ".join(cc_address_list) if len(cc_address_list)>0 else None

                    msg.attach(MIMEText(content))

                    # securing using tls
                    server.starttls(context=self.context)

                    # authenticating with the server to prove our identity
                    server.login(self.username, self.password)

                    # sending a plain text email
                    server.sendmail(self.from_address, [to_address]+cc_address_list, msg.as_string())
                    # server.send_message(msg.as_string())

                    if logfile: logfile.info(f'successfully sent an email to {to_address}')

            except Exception as e:
                if logfile: logfile.error(f'could not send an email to {to_address} - {e}')

