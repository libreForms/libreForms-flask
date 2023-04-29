"""
certification.py: function set for certifying and digitally signing forms

The functions contained in this script are intended to solve a problem outlined in
https://github.com/signebedi/libreForms/issues/8. Specifically, we have users of varying
authorization levels that need - for one reason or another - to sometimes affix their 
digital signature to a form. To click 'submit' or 'approve' is sometimes not enough. Some forms
require users to affix their signatures to 'certify' their forms. Likewise, some managers 
will need the same ability to certify their approval. This process needs to be a little bit more 
than just 'a user hits submit, and the form is certified'. This set of scripts are a response to 
asking "what the best way to implement user 'digital signatures' of forms in python web application?"

Submitted the following question on Stack Overflow: https://stackoverflow.com/q/74679287/13301284.

An initial thought is to add a `certificate` string / byte field to the user database, see below.

```
    # certificate = db.Column(db.String(100))
    certificate = db.Column(db.LargeBinary())
```

And then use this certificate to hash some other field, like username, email, or full name. 
If we use asymmetric encryption, then we probably need to set up an application-wide CA... 
which strikes me as overkill. It also seems a little overkill to manage a pub/priv key 
for something that really just requires some form of identify verification.

It's not clear whether requiring the user to re-enter their password when they 'sign' a 
document is worthwhile; or if it's worthwhile to further password-protect the key; or 
if it's worthwhile to store in a table separate from the user database.

Alternatively, we can also just generate a symmetric key using one of many specs, including
fernet (https://github.com/fernet/spec/) ... this solution seems like a good starting place.

References:
1. https://stackoverflow.com/a/12646090/13301284
2. https://support.microsoft.com/en-us/office/digital-signatures-and-certificates-8186cd15-e7ac-4a16-8597-22bd163e8e96
3. https://cryptography.io/en/latest/fernet/
4. https://www.geeksforgeeks.org/how-to-encrypt-and-decrypt-strings-in-python/

"""

__name__ = "app.certification"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "2.0.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from cryptography.fernet import Fernet

def generate_symmetric_key():
    
    # eventually we may also want to add support for
    # key rotation using MultiFernet.rotate(), see
    # https://cryptography.io/en/latest/fernet/

    return Fernet.generate_key()

def encrypt_with_symmetric_key(key, base_string):
    fernet = Fernet(key)
    return fernet.encrypt(base_string.encode())

def decrypt_with_symmetric_key(key, encrypted_string):
    fernet = Fernet(key)
    try:
        return fernet.decrypt(encrypted_string).decode()
    except Exception as e: 
        return None

def verify_symmetric_key(key, encrypted_string, base_string):
    if decrypt_with_symmetric_key(key, encrypted_string) == base_string:
        return True
    else:
        return False