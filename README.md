# cpe2stix

A command line tool that turns NVD CPE records into STIX 2.1 Objects.

## Before you get started

If you do not want to backfill, maintain, or support your own CPE STIX objects check out CTI Butler which provides a fully manage database of these objects and more!

https://www.ctibutler.com/

## Overview

Having a standardised way of to describe CPEs becomes very useful when managing software tools you're using. That is where Common Platform Enumerations (CPEs) come in;

> CPE is a structured naming scheme for information technology systems, software, and packages. Based upon the generic syntax for Uniform Resource Identifiers (URI), CPE includes a formal name format, a method for checking names against a system, and a description format for binding text and tests to a name.

We had a requirement to have an up-to-date copy of NVD CPEs in STIX 2.1 format.

The code in this repository turns CPEs into STIX 2.1 objects, and keeps them updated to match the official CPE dictionary;

1. Downloads the current CPEs (that match a users filters) from the NVD API
2. Converts them to STIX 2.1 Objects
3. Stores the STIX 2.1 Objects in the file store
4. Creates STIX Bundles of generated objects for each update run

## tl;dr

[![cpe2stix](https://img.youtube.com/vi/ZIj7Wo0iELc/0.jpg)](https://www.youtube.com/watch?v=ZIj7Wo0iELc)

## Install the script

```shell
# clone the latest code
git clone https://github.com/muchdogesec/cpe2stix
# create a venv
cd cpe2stix
python3 -m venv cpe2stix-venv
source cpe2stix-venv/bin/activate
# install requirements
pip3 install -r requirements.txt
```

You will also need to have redis installed on your machine. [Instructions to do this are here](https://redis.io/docs/getting-started/installation/).

If you're on Mac, like me, the easiest way to do this is;

```shell
brew install redis
```

## Setup configoration options

You will need to create an `.env` file as follows;

```shell
cp .env.example .env
```

You will then need to set te variables as follows;

* `NVD_API_KEY` (required): your NVD API key. Get one for free here: https://nvd.nist.gov/developers/start-here
	* note, the script will work without it, but it is very likely you will run into rate limit errors.
* `CPE_LAST_MODIFIED_EARLIEST` (required): the earliest CPE date you want results for. CPEs with a value less than `cpe.lastModified` time will be ignored. Enter in format `YYYY-MM-DDThh:mm:ss`. Note, the script will use the NVD APIs `lastModStartDate` parameter for this.
* `CPE_LAST_MODIFIED_LATEST` (required): default is script run time. CPEs with a `cpe.lastModified` greater than the time entered will be ignored. Enter in format `YYYY-MM-DDThh:mm:ss`. The script uses the `lastModEndDate` parameter on the NVD API for this.
* `RESULTS_PER_PAGE` (required): default is `1000`. Maximum value allowed is `10000`. Defines the number of results per page to be returned on the NVD API (using the `resultsPerPage` parameter). This does not change the data returned by the script. It is designed to reduce timeouts when large pages are returned.

IMPORTANT: if the time between `CPE_LAST_MODIFIED_EARLIEST` and `CPE_LAST_MODIFIED_LATEST` is greater than 120 days, the script will batch celery jobs with different `lastModStartDate` and `lastModEndDate` as NVD only allows for a range of 120 days to be specified in a request.

## Running the script

The script runs Redis and Celery jobs to download the data, you must start this first.

Generally you want to run these in a seperate terminal window but still in the a `cpe2stix-venv`.

```shell
# navigate to the root of cpe2stix install
cd cpe2stix
# activate venv
source cpe2stix-venv/bin/activate
# restart redis
brew services restart redis
# start celery
celery -A cpe2stix.celery worker --loglevel=info --purge
```

If you continually run into issues, you can also use flower to monitor Celery workers for debugging. In a new terminal run;

```shell 
celery -A cpe2stix.celery flower
```

To open the application. You can also use Docker to run flower, [as detailed here](https://flower.readthedocs.io/en/latest/install.html#usage).

The script to get CPEs can now be executed (in the second terminal window) using;

```shell
python3 cpe2stix.py
```

It will also filter the data created using any values entered in the `.env` file on each run.

On each run, the old `stix2_objects/cpe-bundle.json` will be overwritten.

When the data conversion is complete you must kill the celery worker before running the script again. Failure to do so will lead to issues with the bundle IDs.

```shell
^C
worker: Hitting Ctrl+C again will terminate all running tasks!

worker: Warm shutdown (MainProcess)
```

Don't forget to restart the workers again, as follows;

```shell
# start celery
celery -A cpe2stix.celery worker --loglevel=info --purge
```

## Mapping information

BEFORE CONTINUING: [I STRONGLY recommend you read our blog on CVE/CPE API responses](https://www.dogesec.com/blog/converting_cve_cpe_to_stix_objects/), and the logic to interpret them. The blog can be found here. It is also linked at the bottom of this readme. This code is built around that logic.

### Marking Definition / Identity

These are hardcoded and imported from our [stix4doge repository](https://github.com/muchdogesec/stix4doge). Specifically these objects;

* Marking Definition: https://raw.githubusercontent.com/muchdogesec/stix4doge/main/objects/marking-definition/cpe2stix.json

### Software

cpe2stix creates Software SCOs for CPEs as follows;

```json
{
    "type": "software",
    "spec_version": "2.1",
    "id": "software--<GENERATED BY STIX2 LIBRARY>",
    "name": "<products.cpe.titles.title> (if multiple, where lan = en, else first result)",
    "cpe": "<products.cpe.cpeName>",
    "swid": "<products.cpe.cpeNameId>",
    "version": "<products.cpe.cpeName[version_section]>",
    "vendor": "<products.cpe.cpeName[vendor_section]>",
    "languages": [
        "<products.cpe.titles.lang>"
    ],
    "object_marking_refs": [
        "marking-definition--94868c89-83c2-464b-929b-a1a8aa3c8487",
        "<IMPORTED MARKING DEFINTION OBJECT>"
    ]
}
```

Note, if the NVD API record contains the property `products.cpe.deprecated` then `[DEPRECATED]` is added to the `name` property.

### Bundle

All objects will be packed into a bundle file in `stix2_objects` names `cpe-bundle.json` which has the following structure.

```json
{
    "type": "bundle",
    "id": "bundle--<UUIDV5 GENERATION LOGIC>",
    "objects": [
        "<ALL STIX JSON OBJECTS>"
    ]
}
```

To generate the id of the SRO, a UUIDv5 is generated using the namespace `5e6fc5ec-e507-52e7-8465-cf5ffc47138a` and an md5 hash of all the sorted objects in the bundle.

### Updating STIX Objects

New CPEs are added weekly. Existing CPEs are also updated.

Therefore the script can be used to keep an up-to-date copy of objects.

Generally it is assumed the script will be used like so;

1. on install, a user will create a backfill of all CPEs (almost 1.2 million at the time of writing, depending on `CPE_LAST_MODIFIED_EARLIEST`/`CPE_LAST_MODIFIED_LATEST` date used)
    * note, generally this job will be split into multiple parts, downloading one year of data at a time.
2. said bundle(s) will be imported to some downstream tool (e.g. a threat intelligence platform)
3. the user runs the script again, this time updating the `CPE_LAST_MODIFIED_EARLIEST` variable to match the last time script is run (so that updated bundle only captures new and update objects)

The script will store the STIX objects created in the `stix2_objects` directory. All old objects will be purged with each run.

## Recommendations for backfill

I STRONGLY recommend you [use cxe2stix_helper to perform the backfill](https://github.com/muchdogesec/cxe2stix_helper). cxe2stix_helper will handle the splitting of the bundle files into your desired time ranges.

Note, [you can easily download historic CPE data from our cti_knowledge_base repository so you don't have to run this script](https://github.com/muchdogesec/cti_knowledge_base_store).

## Useful supporting tools

* To generate STIX 2.1 Objects: [stix2 Python Lib](https://stix2.readthedocs.io/en/latest/)
* The STIX 2.1 specification: [STIX 2.1 docs](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
* [NVD CPE Overview](https://nvd.nist.gov/products)
* [NVD CVE API](https://nvd.nist.gov/developers/products)

## Support

[Minimal support provided via the DOGESEC community](https://community.dogesec.com/).

## License

[Apache 2.0](/LICENSE).