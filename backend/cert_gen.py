"""
Automatic Self-Signed SSL Certificate Generator for OmniControl.
Enables HTTPS for mobile browsers (Chrome / Safari) to unlock
DeviceMotionEvent and DeviceOrientationEvent on local network.
"""

import os
import sys
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def ensure_ssl_certs(local_ip: str, base_dir: str = None) -> tuple[str, str]:
    """
    Ensure SSL certificates exist for the given local IP address.
    Generates a 2048-bit RSA self-signed certificate with SAN entries
    for localhost, 127.0.0.1, and the current local LAN IP.
    """
    if base_dir is None:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    certs_dir = os.path.join(base_dir, "certs")
    os.makedirs(certs_dir, exist_ok=True)
    
    cert_path = os.path.join(certs_dir, "cert.pem")
    key_path = os.path.join(certs_dir, "key.pem")

    # If certs already exist and are non-empty, reuse them
    if (os.path.exists(cert_path) and os.path.getsize(cert_path) > 0 and
            os.path.exists(key_path) and os.path.getsize(key_path) > 0):
        return cert_path, key_path

    # Generate new RSA private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip or "omnicontrol.local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OmniControl Local"),
    ])

    san_entries = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    if local_ip:
        try:
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except ValueError:
            san_entries.append(x509.DNSName(local_ip))

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))  # ~2 years valid
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_path, key_path
