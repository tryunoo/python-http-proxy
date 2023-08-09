from OpenSSL import crypto
import random
import socket
import ssl
import os
from proxy import util


def get_private_key(private_key_path):
    if not os.path.isfile(private_key_path):
        util.print_error_exit("%s is not exist." % private_key_path)

    with open(private_key_path, 'rb') as f:
        private_key_pem = f.read()
        try:
            private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key_pem)
        except:
            util.print_error_exit("Cannot load private key (%s)" % private_key_path)

    return private_key, private_key_pem


def get_cacert(cacert_path):
    if not os.path.isfile(cacert_path):
        util.print_error_exit("%s is not exist." % cacert_path)

    with open(cacert_path, 'rb') as f:
        cacert_pem = f.read()
        try:
            cacert = crypto.load_certificate(crypto.FILETYPE_PEM, cacert_pem)
        except:
            util.print_error_exit("Cannot load cacert (%s)" % cacert_path)

    return cacert, cacert_pem


def get_server_certificate(host, port):
    context = ssl.create_default_context()
    with socket.create_connection((host, port)) as sock:
        with context.wrap_socket(sock, server_hostname=host) as sslsock:
            der_cert = sslsock.getpeercert(True)
            return ssl.DER_cert_to_PEM_cert(der_cert)  


def get_target_cert_informations(host, port):
    cert = get_server_certificate(host, port)
    x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert)

    subject = x509.get_subject()

    altname = host.encode('utf-8')
    for i in range(x509.get_extension_count()):
        x509extension_obj = x509.get_extension(i)
        if x509extension_obj.get_short_name() == b'subjectAltName':
            altname = str(x509extension_obj).encode('utf-8')

    return subject, altname


def generate_keypair():
    keypair = crypto.PKey()
    keypair.generate_key(crypto.TYPE_RSA, 2048)

    return keypair


def create_cacert(private_key):
    serialnumber = random.getrandbits(64)

    cacert = crypto.X509()
    cacert.get_subject().CN = 'test'
    cacert.get_subject().C = 'JP'
    cacert.get_subject().ST = 'test'
    cacert.get_subject().L = 'test'
    cacert.get_subject().O = 'test'
    cacert.get_subject().OU = 'test'
    cacert.gmtime_adj_notBefore(0)
    cacert.gmtime_adj_notAfter(31536000)
    cacert.set_serial_number(serialnumber)
    cacert.set_issuer(cacert.get_subject())
    cacert.set_version(2)
    cacert.set_pubkey(private_key)

    cacert.add_extensions([
        crypto.X509Extension(b'basicConstraints', False, b'CA:TRUE'),
    ])

    cacert.sign(private_key, 'sha256')

    cacert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cacert)

    return cacert, cacert_pem


def create_csr(private_key, subject):
    # create self-signed cert
    csr = crypto.X509Req()
    if subject.CN is not None: csr.get_subject().CN = subject.CN
    if subject.C is not None: csr.get_subject().C = subject.C
    if subject.ST is not None: csr.get_subject().ST = subject.ST
    if subject.L is not None: csr.get_subject().L = subject.L
    if subject.O is not None: csr.get_subject().O = subject.O
    if subject.OU is not None: csr.get_subject().OU = subject.OU

    csr.set_version(2)
    csr.set_pubkey(private_key)
    csr.sign(private_key, 'sha256')

    return csr


def create_server_cert(host, port, private_key, cacert):
    subject, altname = get_target_cert_informations(host, port)

    csr = create_csr(private_key, subject)

    server_cert = crypto.X509()
    serialnumber = random.getrandbits(64)
    server_cert.set_serial_number(serialnumber)
    server_cert.gmtime_adj_notBefore(0)
    server_cert.gmtime_adj_notAfter(31536000)
    server_cert.set_subject(csr.get_subject())

    server_cert.set_issuer(cacert.get_subject())

    server_cert.add_extensions([
        crypto.X509Extension(b'extendedKeyUsage', False, b'serverAuth'),
        crypto.X509Extension(b'subjectAltName', False, altname),
        crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
    ])

    server_cert.set_version(2)
    server_cert.set_pubkey(csr.get_pubkey())
    server_cert.sign(private_key, "sha256")

    server_cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, server_cert)

    return server_cert, server_cert_pem
