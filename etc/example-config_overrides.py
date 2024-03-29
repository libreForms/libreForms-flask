import os

config = {
    'domain': os.environ['LIBREFORMS_DOMAIN'], # this needs to be configured to work correctly
    'default_user_email': os.environ['LIBREFORMS_USER_EMAIL'] if os.environ['LIBREFORMS_USER_EMAIL'] else 'libreforms@example.com',
    'smtp_enabled': True if os.environ['SMTP_ENABLED'] == 'True' else False,
    'smtp_mail_server':os.environ['SMTP_MAIL_SERVER'],
    'smtp_port':os.environ['SMTP_PORT'],
    'smtp_username':os.environ['SMTP_USERNAME'],
    'smtp_password':os.environ['SMTP_PASSWORD'],
    'smtp_from_address':os.environ['SMTP_FROM_ADDRESS'],
    'enable_email_verification': True if os.environ['SMTP_ENABLED'] == 'True' else False,
    'allow_password_resets': True if os.environ['SMTP_ENABLED'] == 'True' else False,
    'enable_reports': True if os.environ['SMTP_ENABLED'] == 'True' else False,
    'allow_anonymous_form_submissions': True if os.environ['SMTP_ENABLED'] == 'True' else False,
    'mongodb_user':os.environ['MONGODB_USERNAME'] if os.environ['MONGODB_USERNAME'] else None,
    'mongodb_host':os.environ['MONGODB_HOSTNAME'] if os.environ['MONGODB_HOSTNAME'] else None,
    'mongodb_pw':os.environ['MONGODB_PASSWORD'] if os.environ['MONGODB_PASSWORD'] else None,
    'celery_broker':os.environ['CELERY_BROKER'],
    'celery_backend':os.environ['CELERY_BACKEND'],
}