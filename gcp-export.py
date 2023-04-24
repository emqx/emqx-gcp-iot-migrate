#!/usr/bin/env python

"""
Usage:

    python gcp-export.py \\
      --project=my-project-id \\
      --region=us-central1 \\
      --service-account-json=$HOME/service_account.json \\

--service-account-json is optional if you have set ADC (Application Default Credentials)
with gcloud auth application-default login
"""

import argparse
import base64
import json
import os

from google.cloud import iot_v1
from google.protobuf import field_mask_pb2 as gp_field_mask


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--project",
        required=True,
        help="GCP Project",
    )
    parser.add_argument(
        "--registry",
        required=True,
        help="GCP IoT Registry",
    )

    parser.add_argument(
        "--region",
        required=True,
        help="GCP Region",
    )

    parser.add_argument(
        "--service-account-json",
        type=argparse.FileType("r"),
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        help="Path to service account json file.",
    )

    args = parser.parse_args()

    if args.service_account_json:
        client = iot_v1.DeviceManagerClient.from_service_account_json(
            args.service_account_json.name
        )
    else:
        client = iot_v1.DeviceManagerClient()
    registry_path = client.registry_path(args.project, args.region, args.registry)

    fields = gp_field_mask.FieldMask(
        paths=["id", "name", "num_id", "credentials", "blocked", "config"]
    )

    devices = list(
        client.list_devices(request={"parent": registry_path, "field_mask": fields})
    )

    print(
        json.dumps(
            [format_device(args, device) for device in devices if not device.blocked],
            indent=2,
        )
    )


def format_device(args, device):
    return {
        "registry": [args.project, args.region, args.registry],
        "device_ids": format_device_ids(device),
        "credentials": format_creds(device.credentials),
        "blocked": device.blocked,
        "config": format_config(device.config),
    }


def format_creds(creds):
    return [
        {
            "public_key": {
                "format": format_public_key_format(cred.public_key.format),
                "key": cred.public_key.key,
            },
            "expiration_time": int(cred.expiration_time.timestamp()),
        }
        for cred in creds
    ]


def format_public_key_format(format):
    return str(format).split(".")[-1]


def format_config(config):
    return base64.b64encode(config.binary_data).decode("utf-8")


def format_device_ids(device):
    return [device.id, device.num_id]


if __name__ == "__main__":
    main()
