
```bash
python gcp-export.py --project "iot-export" --region "europe-west1" --registry "my-registry"
```

```bash
python client-demo.py --project "iot-export" --region "europe-west1" --registry "my-registry" --algorithm ES256 --device "c2-ec-x509" --hostname mqtt.googleapis.com --private-key-file ../keys/c2_ec_private.pem --ca-certs ../keys/google-roots.pem
```

