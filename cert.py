from OpenSSL import crypto
import random
import socket
import ssl

CAKEY_PATH = "ssl/mitmproxy-ca.pem"

def get_cacrt():
    cacrt_path = 'ssl/mitmproxy-ca-cert.pem'
    cacrt_fp = open(cacrt_path, 'r')
    cacrt_data = cacrt_fp.read()
    cacrt =  crypto.load_certificate(crypto.FILETYPE_PEM, cacrt_data)

    return cacrt


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


def create_csr(host, port):
    with open(CAKEY_PATH, 'rb') as f: key = f.read()
    key = crypto.load_privatekey(crypto.FILETYPE_PEM, key)

    subject, altname = get_target_cert_informations(host, port)

    # create self-signed cert
    x509req = crypto.X509Req()
    if subject.CN is not None: x509req.get_subject().CN = subject.CN
    if subject.C is not None: x509req.get_subject().C = subject.C
    if subject.ST is not None: x509req.get_subject().ST = subject.ST
    if subject.L is not None: x509req.get_subject().L = subject.L
    if subject.O is not None: x509req.get_subject().O = subject.O
    if subject.OU is not None: x509req.get_subject().OU = subject.OU

    #x509req.add_extensions([
    #    crypto.X509Extension(
    #        b'basicConstraints', False, b'CA:FALSE'),
    #    crypto.X509Extension(
    #        b'keyUsage', False, b'Digital Signature, Non Repudiation, Key Encipherment'),
    #    crypto.X509Extension(
    #        b'subjectAltName', False, altname)
    #])

    x509req.set_version(3)
    x509req.set_pubkey(key)
    x509req.sign(key, 'sha512')

    csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM, x509req)

    return x509req, csr, altname


def create_server_cert(host, port):
    with open(CAKEY_PATH, 'rb') as f: key = f.read()
    key = crypto.load_privatekey(crypto.FILETYPE_PEM, key)

    x509req, csr, altname = create_csr(host, port)

    x509 = crypto.X509()
    serialnumber = random.getrandbits(64)
    x509.set_serial_number(serialnumber)
    x509.gmtime_adj_notBefore(0)
    x509.gmtime_adj_notAfter(31536000)
    x509.set_subject(x509req.get_subject())

    cacrt = get_cacrt()
    x509.set_issuer(cacrt.get_subject())

    x509.add_extensions([
        #crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
        #crypto.X509Extension(b'ExtendedKeyUsage', False, b'Server Authentication'),
        crypto.X509Extension(b'subjectAltName', False, altname)
    ])
    #x509.add_extensions(x509req.get_extensions())

    x509.set_version(3)
    x509.set_pubkey(x509req.get_pubkey())
    
    #cakey = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
    x509.sign(key, "sha512")

    crt = crypto.dump_certificate(crypto.FILETYPE_PEM, x509)

    return crt
