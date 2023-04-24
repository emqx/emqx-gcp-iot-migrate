# EMQX Compatibility with Google Cloud IoT Core

The Internet of Things (IoT) has experienced significant growth and widespread adoption in recent years.
The IoT ecosystem is also growing rapidly, including a wide range of managed services.

One such service is [Google Cloud IoT Core](https://cloud.google.com/iot-core). It is a fully managed service that allows you to easily and securely connect and manage IoT devices. Google Cloud IoT Core provides HTTP and MQTT protocols for device communication. MQTT is a lightweight publish/subscribe messaging protocol that is widely used in IoT applications.

However, it was recently announced that Google Cloud IoT Core will be retired on August 16, 2023.
This makes customers to search for alternatives to Google Cloud IoT Core.

One of the alternatives for MQTT is [EMQX](https://www.emqx.io/).

EMQX is an open-source, distributed, and scalable MQTT broker that supports various installation methods. Also, a managed service is available for EMQX, which is called [EMQX Cloud](https://www.emqx.com/en/cloud).

In this article, we will show how we can migrate MQTT devices from Google Cloud IoT Core to EMQX.

## The problem

One of the problems that we face when migrating from Google Cloud IoT Core to other MQTT brokers is that Google Cloud IoT Core uses a specific domain model, that wraps the MQTT protocol. The central concept in Google Cloud IoT Core is the _device_. A device is a logical representation of a physical device. The devices
* are grouped in _registries_;
* are identified by a unique _device ID_, which is a string, or by an automatically assigned _device number_;
* have a _public key_ that is used to authenticate the device when it connects to the MQTT broker;
* have an associated _config_, which is an opaque blob of data that devices can receive from the MQTT broker.

At the same time, when we try to use an alternative MQTT broker, we expect to make minimal changes to the device code.

To achieve this, EMQX provides a compatibility layer that simplifies the migration. This layer supports:
* importing device config and authentication data from Google Cloud IoT Core;
* providing MQTT authentication in Google Cloud IoT Core compatible format;
* providing device config in a Google Cloud IoT Core compatible manner.

## Initial setup

In the initial setup, we have the following components.

* A project and activated Google Cloud IoT Core service:
```
>gcloud projects list
PROJECT_ID  NAME        PROJECT_NUMBER
iot-export  IoT Export  283634501352
>gcloud services list
NAME                                 TITLE
...
cloudiot.googleapis.com              Cloud IoT API
...
```
* An IoT registry named `my-registry`:
```
>gcloud iot registries list --region europe-west1 --project iot-export
ID           LOCATION      MQTT_ENABLED
my-registry  europe-west1  MQTT_ENABLED
```
* Some devices in the registry:
Public keys are assigned to the devices. E.g.:
```
>gcloud iot devices describe c2-ec-x509 --region europe-west1 --registry my-registry --project iot-export
config:
  binaryData: AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0-P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn-AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq-wsbKztLW2t7i5uru8vb6_wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t_g4eLj5OXm5-jp6uvs7e7v8PHy8_T19vf4-fr7_P3-_w==
  cloudUpdateTime: '2023-04-12T14:01:34.862851Z'
  deviceAckTime: '2023-04-19T09:15:53.458746Z'
  version: '2'
credentials:
- expirationTime: '1970-01-01T00:00:00Z'
  publicKey:
    format: ES256_X509_PEM
    key: |
      -----BEGIN CERTIFICATE-----
      MIIBEjCBuAIJAPKVZoroXatKMAoGCCqGSM49BAMCMBExDzANBgNVBAMMBnVudXNl
      ZDAeFw0yMzA0MTIxMzQ2NTJaFw0yMzA1MTIxMzQ2NTJaMBExDzANBgNVBAMMBnVu
      dXNlZDBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABAugsuay/y2SpGEVDKfiVw9q
      VHGdZHvLXDqxj9XndUi6LEpA209ZfaC1eJ+mZiW3zBC94AdqVu+QLzS7rPT72jkw
      CgYIKoZIzj0EAwIDSQAwRgIhAMBp+1S5w0UJDuylI1TJS8vXjWOhgluUdZfFtxES
      E85SAiEAvKIAhjRhuIxanhqyv3HwOAL/zRAcv6iHsPMKYBt1dOs=
      -----END CERTIFICATE-----
gatewayConfig: {}
id: c2-ec-x509
lastConfigAckTime: '2023-04-19T09:15:53.450757285Z'
lastConfigSendTime: '2023-04-19T09:15:53.450839281Z'
lastErrorStatus:
  code: 9
  message: 'mqtt: The connection broke or was closed by the client.'
lastErrorTime: '2023-04-19T08:50:38.285599550Z'
lastEventTime: '1970-01-01T00:00:00Z'
lastHeartbeatTime: '1970-01-01T00:00:00Z'
name: projects/iot-export/locations/europe-west1/registries/my-registry/devices/2928540609735937
numId: '2928540609735937'
```
Note `config` and `credentials` fields.

Let us see, how an actual device (i.e. client) interacts with the MQTT endpoint. We have a [test script](https://github.com/emqx/emqx-gcp-iot-migrate/blob/main/client-demo.py), that connects to the endpoint, authenticates with the private key and obtains config. The code is a slightly modified version of the official [code examples](https://github.com/GoogleCloudPlatform/python-docs-samples/blob/HEAD/iot/api-client/mqtt_example/cloudiot_mqtt_example.py) for Python.

Install the environment:
```bash
git clone https://github.com/emqx/emqx-gcp-iot-migrate.git
cd emqx-gcp-iot-migrate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Fetch google root certificates:
```bash
curl "https://pki.google.com/roots.pem" --location --output google-roots.pem
```

Run the script:
```bash
python client-demo.py --project "iot-export" --region "europe-west1" --registry "my-registry" --algorithm ES256 --device "c2-ec-x509" --hostname mqtt.googleapis.com --private-key-file ./sample-keys/c2_ec_private.pem --ca-certs ./google-roots.pem
```

The output is:
```
Device client_id is 'projects/iot-export/locations/europe-west1/registries/my-registry/devices/c2-ec-x509'
Password is eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2ODIzMzQyNzksImV4cCI6MTY4MjMzNTQ3OSwiYXVkIjoiaW90LWV4cG9ydCJ9.djolGOTtK7OxYN1xh1HmEdNCUPFNNpTg8AA9dAO3wnqUByyZYu6OwmSBDRsb89EfWkxLR5Pszc_fsv5gGv_Fpw
Subscribing to config topic /devices/c2-ec-x509/config
on_connect Connection Accepted.
Received message b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff' on topic /devices/c2-ec-x509/config with qos 1
```
We see the following:
* The client connects to the endpoint with the specially crafted `client_id`.
* It crafts a JWT token and uses it as a password (Google Cloud IoT Core-specific way of authentication).
* It subscribes to the config topic, also following the Google Cloud IoT Core convention.
* It receives the config from the config topic. The message is a binary blob but can be a JSON string or something else.

We saw how things work with Google Cloud IoT Core. We expect the same things also work with an MQTT alternative, without modifications to the client code.

## The Migration

For migration, we need:
* export data from Google Cloud IoT Core;
* import data into EMQX.

### Exporting Data from Google Cloud IoT Core

For export, we have a script utilizing the [Google Cloud IoT Core REST API](https://cloud.google.com/iot/docs/reference/cloudiot/rest).

In the same `emqx-gcp-iot-migrate` folder we run:
```bash
python gcp-export.py --project iot-export --region europe-west1 --registry my-registry > gcp-data.json
```

`gcp-data.json` file now contains the data ready for import into EMQX.

### Starting EMQX

The easiest way to try EMQX locally is to use Docker.

```bash
docker run -d --name emqx -p 8883:8883 -p 18083:18083 emqx/emqx:4.4.18
```

8883 is the MQTT port (over TLS), 18083 is the HTTP API port.

### Importing Data into EMQX

To import data into EMQX, we use the REST API.

```bash
curl -s -v -u 'admin:public' -X POST 'http://127.0.0.1:18083/api/v4/gcp_device/import' --data @gcp-data.json
...
{"data":{"imported":7,"errors":0},"code":0}
```

`admin:public` is the default username and password for EMQX.

We see that 7 devices were imported.

### Testing the Migration

We use the same client code as before, but we need to change the endpoint to the EMQX endpoint. We also need to change the CA certificate to the one used by EMQX.

```bash
docker cp emqx:/opt/emqx/etc/certs/cacert.pem ./сacert.pem
python client-demo.py --project "iot-export" --region "europe-west1" --registry "my-registry" --algorithm ES256 --device "c2-ec-x509" --hostname localhost --private-key-file ./sample-keys/c2_ec_private.pem --ca-certs cacert.pem
```
The output is:
```
Device client_id is 'projects/iot-export/locations/europe-west1/registries/my-registry/devices/c2-ec-x509'
Password is eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2ODIzNDE2NzgsImV4cCI6MTY4MjM0Mjg3OCwiYXVkIjoiaW90LWV4cG9ydCJ9.04_zR71fmi0YikSxZbb_wxpVTnikt2XIkxkuI6JM6VS0VJ1B8QrggHuUron8MAOSJDJu9SVa2fuuFFjJEKJ-Bw
Subscribing to config topic /devices/c2-ec-x509/config
on_connect Connection Accepted.
Received message b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff' on topic /devices/c2-ec-x509/config with qos 1
```

This is just the same as before, but now we are using EMQX instead of Google Cloud IoT Core.

## Additional APIs

EMQX provides some additional API calls to manage EMQX data using "device" terminology.

### Config management

To get the config for the device `c2-ec-x509`:
```bash
>curl -s -u 'admin:public' -X GET 'http://127.0.0.1:18083/api/v4/gcp_device/c2-ec-x509/config'
{"data":{"config":"AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/w=="},"code":0}
```

To update the config for the device `c2-ec-x509`:
```bash
>curl -s -u 'admin:public' -X PUT 'http://127.0.0.1:18083/api/v4/gcp_device/c2-ec-x509/config' --data-raw '{"config": "bmV3Y29uZmlnCg=="}'
{"data":{},"code":0}
```

### Credential management

To list individual device credentials:
```bash
>curl -s -u 'admin:public' -X GET 'http://127.0.0.1:18083/api/v4/gcp_device/keys?project=iot-export&location=europe-west1&registry=my-registry&deviceid=c2-ec-x509'
```

To list all credentials:
```bash
>curl -s -u 'admin:public' -X GET 'http://127.0.0.1:18083/api/v4/gcp_device/keys' | jq
{
  "meta": {
    "page": 1,
    "limit": 10000,
    "hasnext": false,
    "count": 42
  },
  "data": [
    {
      "key_type": "RSA_X509_PEM",
      "key": "...",
      "id": [
        "projects/iot-export/locations/europe-west1/registries/my-registry/devices/2820826361193805",
        "AAX6FVqqCxr0QgAACzMAEw=="
      ],
      "extra": {},
      "expires_at": 0,
      "created_at": 1682344505
    },
...
```

Both queries allow pagination: `_limit` and `_page` parameters.

To add and delete individual credentials:
```bash
curl -s -u 'admin:public' -X POST 'http://127.0.0.1:18083/api/v4/gcp_device/keys?project=iot-export&location=europe-west1&registry=my-registry&deviceid=D1' --data-raw '{"key": "-----BEGIN PUBLIC KEY-----\n...", "key_type":"RSA_PEM"}'  | jq
curl -s -u 'admin:public' -X DELETE 'http://127.0.0.1:18083/api/v4/gcp_device/keys?project=iot-export&location=europe-west1&registry=my-registry&deviceid=D1&tag=AAX6Fae%2BMVf0QAAAC1MAAA%3D%3D'
```

Note that the `tag` parameter is required for deletion. This is an auto-generated tag that is assigned to the key when it is created. It can be found in the `id` field of the key in the listing API result.

## Limitations

It should also be noted that the EMQX broker is not a drop-in replacement for Google Cloud IoT Core. The mentioned APIs are provided to help with migration. The most notable limitations are:
* EMQX does not support the "gateway" concept. However, this results only in the inability of devices behind a gateway to have gateway-independent credentials.
* Project, location and registry are not used in EMQX. They are only used to construct or verify Google Cloud IoT Core-compatible client ids. That means that devices imported into EMQX should have globally unique ids to avoid collisions.

## Conclusion

This article has shown how to migrate from Google Cloud IoT Core to EMQX.

The migration process is quite straightforward. The things that are needed to be done are:
* to export the device credentials from Google Cloud IoT Core and import them into EMQX;
* switch the endpoint in the actual devices to the EMQX broker.

An advantage of such a migration is that EMQX in general provides [much more functionality](https://www.emqx.io/docs/en/v4.4) than Google Cloud IoT Core.


