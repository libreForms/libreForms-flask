""" 
saml.py: app saml auth library


"""

__name__ = "app.saml"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.0.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


from onelogin.saml2.settings import OneLogin_Saml2_Settings
from app.config import config 

def generate_saml_config(domain, saml_idp_entity_id, saml_idp_sso_url, saml_idp_slo_url, saml_idp_x509_cert,
                         strict=True, debug=False, saml_name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                         saml_sp_x509_cert="", saml_sp_private_key=""):

    saml_auth = {
        "strict": strict,
        "debug": debug,
        "sp": {
            "entityId": f"{domain}/auth/metadata",
            "assertionConsumerService": {
                "url": f"{domain}/auth/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "singleLogoutService": {
                "url": f"{domain}/auth/sls",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "NameIDFormat": saml_name_id_format,
            "x509cert": saml_sp_x509_cert,
            "privateKey": saml_sp_private_key
        },
        "idp": {
            "entityId": saml_idp_entity_id,
            "singleSignOnService": {
                "url": saml_idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "singleLogoutService": {
                "url": saml_idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": saml_idp_x509_cert
        }
    }
    return saml_auth

def verify_metadata(saml_auth_config):
    saml_settings = OneLogin_Saml2_Settings(saml_auth_config)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)
    return metadata, errors

def generate_metadata_file(output_file:str="config/metadata.xml"):

    metadata, errors = verify_metadata(generate_saml_config(
        domain=config['domain'], 
        saml_idp_entity_id=config['saml_idp_entity_id'], 
        saml_idp_sso_url=config['saml_idp_sso_url'], 
        saml_idp_slo_url=config['saml_idp_slo_url'], 
        saml_idp_x509_cert=config['saml_idp_x509_cert'],
        strict=config['saml_strict'], 
        debug=config['saml_debug'], 
        saml_name_id_format=config['saml_name_id_format'],
        saml_sp_x509_cert=config['saml_sp_x509_cert'], 
        saml_sp_private_key=config['saml_sp_private_key'],
    ))
    
    if len(errors) == 0:
        with open(output_file, "w") as f:
            f.write(metadata)
            print(f"Metadata successfully generated and saved to {output_file}")
    else:
        print("Error(s) found in metadata:")
        for error in errors:
            print(f" - {error}")
