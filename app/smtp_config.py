import hashlib, os, trace, sys, logging, subprocess, smtplib, time
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders
import datetime as dt

class sendMail():
    def __init__(self, mail_server=None, port=None, 
                        username=None, password=None):
        # this is where we initialize the connection to the mail server.

        self.s = smtplib.SMTP(mail_server, port)

        # but... should the directives below come in the send_mail method?
        self.s.starttls() 
        self.s.login(username, password)

    # this function suppresses the log by default but otherwise permits
    # its user to designate a log file to write its success
    def send_mail(self, subject, content, from_address, to_address, attachment=None, logfile=None):
        _from = from_address
        _to = to_address
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = _from
        msg['To'] = _to
        msg.attach(MIMEText(content))

        if attachment != None:
            part = MIMEBase('application', "octet-stream")
            with open(attachment, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)

            part.add_header('Content-Disposition', 'attachment; filename="{}"'.format(os.path.basename(attachment)))
            msg.attach(part)

        self.s.sendmail(_from, _to, msg.as_string())
        self.s.quit()
        if logfile: logfile.info(f'successfully sent an email update to {to_address}\n')