from OpenSSL import crypto
from proxy import cert


def main():
    keypair = cert.generate_keypair()

    _, cacert_pem = cert.create_cacert(keypair)
    private_key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, keypair)

    with open('./proxy/cert/ca-key.pem', 'wb') as f:
        f.write(private_key_pem)

    with open('./proxy/cert/ca-cert.pem', 'wb') as f:
        f.write(cacert_pem)


if __name__ == "__main__":
    main()