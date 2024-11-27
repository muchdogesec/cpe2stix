"""
Helper methods for parsing results from NVD API
"""

import logging
import re
from stix2 import Software, Grouping, Vulnerability, parse, Bundle
from .config import Config
from stix2extensions._extensions import software_cpe_properties_ExtensionDefinitionSMO

logger = logging.getLogger(__name__)


def parse_cpe_api_response(cpe_content, config):
    for cpe_item in cpe_content["products"]:
        cpe = cpe_item['cpe']
        config.LAST_MODIFIED_TIME=cpe["lastModified"].split(".")[0]
        cpe_struct = cpe_name_as_dict(cpe['cpeName'])

        software_dump= {
            "name": cpe["titles"][0]["title"],
            "cpe": cpe['cpeName'],
            "version": cpe_struct['version'],
            "vendor": cpe_struct['vendor'],
            "swid": cpe.get("cpeNameId", ""),
            "languages": list(set([title.get("lang") for title in cpe.get("titles")])),
            "object_marking_refs": [config.TLP_CLEAR_MARKING_DEFINITION]+[config.CPE2STIX_MARKING_DEFINITION_REF.get("id")],
            "extensions": {
                software_cpe_properties_ExtensionDefinitionSMO.id: {
                    "extension_type": "toplevel-property-extension"
                }
            }
        }
        if bool(cpe.get("deprecated", False)):
            software_dump["name"]= f"[DEPRECATED] {cpe['titles'][0]['title']}"

        software = Software(**software_dump, allow_custom=True, x_cpe_struct=cpe_struct)
        config.fs.add(software)
        # responses.append(software.serialize())
    # return responses

def split_cpe_name(cpename: str) -> list[str]:
    """
    Split CPE 2.3 into its components, accounting for escaped colons.
    """
    non_escaped_colon = r"(?<!\\):"
    split_name = re.split(non_escaped_colon, cpename)
    return split_name

def cpe_name_as_dict(cpe_name: str) -> dict[str, str]:
    splits = split_cpe_name(cpe_name)[1:]
    return dict(zip(['cpe_version', 'part', 'vendor', 'product', 'version', 'update', 'edition', 'language', 'sw_edition', 'target_sw', 'target_hw', 'other'], splits))
    
