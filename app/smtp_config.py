import os
import ssl
import smtplib 
import datetime as dt

# borrowed shamelessly from 
# https://www.aabidsofi.com/posts/sending-emails-with-aws-ses-and-python/

def send_email_with_ses(from_address, to_address, content,
                            mail_server, port,username, password):

# getting the credentials fron evironemnt
# host = os.environ.get("SES_HOST_ADDRESS")
# user = os.environ.get("SES_USER_ID")
# password = os.environ.get("SES_PASSWORD")

    # setting up ssl context
    context = ssl.create_default_context()

    # creating an unsecure smtp connection
    with smtplib.SMTP(mail_server,port) as server :

        # securing using tls
        server.starttls(context=context)

        # authenticating with the server to prove our identity
        server.login(username, password)

        # sending a plain text email
        server.sendmail(from_address, to_address, content)
