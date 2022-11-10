from OpenSSL import crypto
import cert


def main():
    keypair = cert.generate_keypair()

    _, cacert_pem = cert.create_cacert(keypair)
    private_key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, keypair)

    with open('./ssl/ca-key.pem', 'wb') as f:
        f.write(private_key_pem)

    with open('./ssl/ca-cert.pem', 'wb') as f:
        f.write(cacert_pem)


if __name__ == "__main__":
    main()