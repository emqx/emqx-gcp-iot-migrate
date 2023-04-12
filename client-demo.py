import argparse
import datetime
import logging
import ssl

import jwt
import paho.mqtt.client as mqtt


def create_jwt(project, private_key, algorithm):

    token = {
        "iat": datetime.datetime.now(tz=datetime.timezone.utc),
        "exp": datetime.datetime.now(tz=datetime.timezone.utc)
        + datetime.timedelta(minutes=20),
        "aud": project
    }

    return jwt.encode(token, private_key, algorithm)


def on_message(_unused_client, _unused_userdata, message):
    print(
        f"Received message {message.payload} on topic {message.topic} with qos {message.qos}"
    )

def on_connect(unused_client, unused_userdata, unused_flags, rc):
    print("on_connect", mqtt.connack_string(rc))

def main():
    parser = argparse.ArgumentParser(
        description=("Example Google Cloud IoT Core MQTT client")
    )
    parser.add_argument(
        "--algorithm",
        choices=("RS256", "ES256"),
        required=True,
        help="Which encryption algorithm to use to generate the JWT.",
    )
    parser.add_argument(
        "--ca-certs",
        required=True,
        help="CA root from https://pki.google.com/roots.pem",
    )
    parser.add_argument(
        "--region",
        required=True,
        help="GCP region"
    )

    parser.add_argument(
        "--device",
        required=True,
        help="Cloud IoT Core device id"
    )
    parser.add_argument(
        "--hostname",
        required=True,
        help="MQTT host",
    )
    parser.add_argument(
        "--port",
        default=8883,
        type=int,
        help="MQTT port",
    )
    parser.add_argument(
        "--private-key-file",
        type=argparse.FileType("r"),
        required=False,
        help="Path to private key file"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="GCP cloud project name",
    )
    parser.add_argument(
        "--registry",
        required=True,
        help="Cloud IoT Core registry id"
    )

    args = parser.parse_args()

    client_id = f"projects/{args.project}/locations/{args.region}/registries/{args.registry}/devices/{args.device}"
    print(f"Device client_id is '{client_id}'")

    client = mqtt.Client(client_id=client_id)

    if args.private_key_file:
        client.username_pw_set(
            username="unused",
            password=create_jwt(
                args.project,
                args.private_key_file.read(),
                args.algorithm
            )
        )

    client.tls_set(ca_certs=args.ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    client.on_message = on_message
    client.on_connect = on_connect

    client.connect(args.hostname, args.port)

    config_topic = f"/devices/{args.device}/config"
    client.subscribe(config_topic, qos=1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    main()
