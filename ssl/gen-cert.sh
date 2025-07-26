#!/bin/bash

# Generate a private key.
openssl genrsa -out key.pem 2048

# Generate a self-signed certificate using the private key
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
  -subj "/C=AU/ST=SomeState/L=SomeCity/O=YourOrg/OU=YourUnit/CN=simple.local"