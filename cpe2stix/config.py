from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import os
import json
import requests
from dotenv import load_dotenv
from stix2 import FileSystemStore


load_dotenv()

CVE2STIX_FOLDER = Path(os.path.abspath(__file__)).parent
REPO_FOLDER = CVE2STIX_FOLDER.parent

STIX2_OBJECTS_FOLDER = REPO_FOLDER / "stix2_objects"

logger = logging.getLogger(__name__)

def load_file_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error loading JSON from {url}: {e}")
        return None

def validate_date_from_env(key):
    try:
        value = os.getenv(key)
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        return value
    except:
        return None

@dataclass
class Config:
    type: str = "cpe"
    LAST_MODIFIED_TIME = os.getenv('CPE_LAST_MODIFIED_EARLIEST')
    start_date: str = validate_date_from_env('CPE_LAST_MODIFIED_EARLIEST')
    end_date: str = validate_date_from_env('CPE_LAST_MODIFIED_LATEST') if os.getenv("CPE_LAST_MODIFIED_LATEST") else datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    stix2_objects_folder: str = str(os.getenv('CTI_DATA_FOLDER_CPE') if os.getenv('CTI_DATA_FOLDER_CPE') else STIX2_OBJECTS_FOLDER)
    stix2_bundles_folder: str = str(os.getenv('CTI_DATA_FOLDER_CPE') if os.getenv('CTI_DATA_FOLDER_CPE') else STIX2_OBJECTS_FOLDER)
    store_in_filestore: bool = True
    disable_parsing: bool = False
    nvd_cpe_api_endpoint: str = "https://services.nvd.nist.gov/rest/json/cpes/2.0/"
    results_per_page: int = int(os.getenv('RESULTS_PER_PAGE', 5_000))
    nvd_api_key: str = os.getenv('NVD_API_KEY')
    file_system: str = str(os.getenv('CTI_DATA_FOLDER_CPE') if os.getenv('CTI_DATA_FOLDER_CPE') else STIX2_OBJECTS_FOLDER)
    if not os.path.exists(file_system):
        os.makedirs(file_system)
    data_path = REPO_FOLDER

    CPE2STIX_MARKING_DEFINITION_URL = "https://raw.githubusercontent.com/muchdogesec/stix4doge/main/objects/marking-definition/cpe2stix.json"
    CPE2STIX_MARKING_DEFINITION_REF = json.loads(load_file_from_url(url=CPE2STIX_MARKING_DEFINITION_URL))
    TLP_CLEAR_MARKING_DEFINITION = "marking-definition--94868c89-83c2-464b-929b-a1a8aa3c8487"

    @property
    def fs(self):
        return FileSystemStore(self.file_system)