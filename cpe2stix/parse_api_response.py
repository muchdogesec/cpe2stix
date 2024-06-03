"""
Helper methods for parsing results from NVD API
"""

import logging
from stix2 import Software, Grouping, Vulnerability, parse, Bundle
from .config import Config

logger = logging.getLogger(__name__)


def parse_cpe_api_response(cpe_content, config):
    for cpe_item in cpe_content["products"]:
        cpe = cpe_item['cpe']
        config.LAST_MODIFIED_TIME=cpe["lastModified"].split(".")[0]
        software_dump= {
            "name": cpe["titles"][0]["title"],
            "cpe": cpe["cpeName"],
            "version": cpe["cpeName"].split(":")[5],
            "vendor": cpe["cpeName"].split(":")[3],
            "swid": cpe.get("cpeNameId", ""),
            "languages": [title.get("lang") for title in cpe.get("titles")],
            "object_marking_refs": [config.TLP_CLEAR_MARKING_DEFINITION]+[config.CPE2STIX_MARKING_DEFINITION_REF.get("id")]
        }
        if bool(cpe.get("deprecated", False)):
            software_dump["name"]= f"[DEPRECATED] {cpe['titles'][0]['title']}"

        software = Software(**software_dump, allow_custom=True)
        config.fs.add(software)
        # responses.append(software.serialize())
    # return responses
