import os
import ssl
import smtplib 
import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class sendMail():
    def __init__(self, mail_server=None, port=None, 
                        username=None, password=None, from_address=None):

        # setting up ssl context
        self.context = ssl.create_default_context()
        self.mail_server = mail_server
        self.port = port
        self.username = username
        self.password = password
        self.from_address = from_address

    # borrowed shamelessly from 
    # https://www.aabidsofi.com/posts/sending-emails-with-aws-ses-and-python/
    def send_mail(self, subject=None, content=None, to_address=None, logfile=None):

        try:
            # creating an unsecure smtp connection
            with smtplib.SMTP(self.mail_server,self.port) as server:

                msg = MIMEMultipart()
                msg['Subject'] = subject
                msg['From'] = self.from_address
                msg['To'] = to_address
                msg.attach(MIMEText(content))

                # securing using tls
                server.starttls(context=self.context)

                # authenticating with the server to prove our identity
                server.login(self.username, self.password)

                # sending a plain text email
                server.sendmail(self.from_address, to_address, msg.as_string())

                if logfile: logfile.info(f'successfully sent an email to {to_address}\n')

        except Exception as e:
            if logfile: logfile.error(f'could not send an email to {to_address} - {e}\n')

