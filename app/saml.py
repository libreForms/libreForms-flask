""" 
saml.py: app saml auth library


"""

__name__ = "app.saml"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


from onelogin.saml2.settings import OneLogin_Saml2_Settings
from app.config import config 

def generate_saml_config(domain, idp_entity_id, idp_sso_url, idp_slo_url, idp_x509_cert,
                         strict=True, debug=False, name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                         sp_x509_cert="", sp_private_key=""):

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
            "NameIDFormat": name_id_format,
            "x509cert": sp_x509_cert,
            "privateKey": sp_private_key
        },
        "idp": {
            "entityId": idp_entity_id,
            "singleSignOnService": {
                "url": idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "singleLogoutService": {
                "url": idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": idp_x509_cert
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
        idp_entity_id=config['idp_entity_id'], 
        idp_sso_url=config['idp_sso_url'], 
        idp_slo_url=config['idp_slo_url'], 
        idp_x509_cert=config['idp_x509_cert'],
        strict=config['strict'], 
        debug=config['debug'], 
        name_id_format=config['name_id_format'],
        sp_x509_cert=config['sp_x509_cert'], 
        sp_private_key=config['sp_private_key'],
    ))
    
    if len(errors) == 0:
        with open(output_file, "w") as f:
            f.write(metadata)
            print(f"Metadata successfully generated and saved to {output_file}")
    else:
        print("Error(s) found in metadata:")
        for error in errors:
            print(f" - {error}")
