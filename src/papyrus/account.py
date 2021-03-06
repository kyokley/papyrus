import sha3
import qrcode_terminal

from bitmerchant.wallet import Wallet
from bitmerchant.network import BitcoinTestNet, BitcoinMainNet
from ecdsa import SigningKey, SECP256k1
from lockbox import encrypt

class PapyrusException(Exception):
    pass

class Account(object):
    def __init__(self,
                 pub_key=None,
                 priv_key=None,
                 address=None,
                 network=None,
                 ):
        if not pub_key and not priv_key:
            raise ValueError('A private or public key must be provided')

        self._pub_key = pub_key
        self._priv_key = priv_key
        self._address = address
        self._network = network

    def __str__(self):
        if self.has_private_keys:
            return 'Private: {priv}\nPublic: {pub}\nAddress: {addr}'.format(
                        priv=self.priv_key(),
                        pub=self.pub_key(),
                        addr=self.address())
        else:
            return 'Public: {pub}\nAddress: {addr}'.format(
                        pub=self.pub_key(),
                        addr=self.address())

    @property
    def has_private_keys(self):
        return bool(self._priv_key)

    def pub_key(self):
        raise NotImplementedError('This function must be overridden by subclasses')

    def priv_key(self):
        raise NotImplementedError('This function must be overridden by subclasses')

    def address(self):
        raise NotImplementedError('This function must be overridden by subclasses')

    @classmethod
    def generate(cls):
        raise NotImplementedError('This function must be overridden by subclasses')

    def print_qrcode(self):
        print('Address: ')
        qrcode_terminal.draw(self._address)

    def encrypted_priv_key(self, passphrase):
        return encrypt(passphrase, self.priv_key())

class EthereumAccount(Account):
    @classmethod
    def generate(cls):
        priv_key = SigningKey.generate(curve=SECP256k1)
        pub_key = priv_key.get_verifying_key()

        return cls(pub_key=pub_key,
                   priv_key=priv_key)

    def pub_key(self):
        if not self._pub_key:
            self._pub_key = self._priv_key.get_verifying_key()

        return self._pub_key.to_string().hex()

    def priv_key(self):
        if not self.has_private_keys:
            raise ValueError('This Account object does not contain private keys')

        return self._priv_key.to_string().hex()

    def address(self):
        if not self._address:
            keccak = sha3.keccak_256()
            keccak.update(self._pub_key.to_string())

            self._address = '0x' + keccak.hexdigest()[24:]

        return self._address

class BitcoinAccount(Account):
    def __init__(self,
                 pub_key=None,
                 priv_key=None,
                 address=None,
                 network=None,
                 ):
        if network not in (BitcoinTestNet, BitcoinMainNet):
            raise ValueError('A valid network must be provided')

        super().__init__(pub_key=pub_key,
                         priv_key=priv_key,
                         address=address,
                         network=network,
                         )

    @classmethod
    def generate(cls, extra_entropy=None, testnet=False):
        network = BitcoinMainNet if not testnet else BitcoinTestNet
        wallet = Wallet.new_random_wallet(extra_entropy, network=network)
        child_account = wallet.get_child(0, is_prime=True)

        return cls(pub_key=child_account.serialize_b58(private=False),
                   priv_key=child_account.serialize_b58(private=True),
                   network=network,
                   )

    def pub_key(self):
        if not self._pub_key:
            wallet = Wallet.deserialize(self._priv_key, network=self._network)
            self._pub_key = wallet.serialize_b58(private=False)

        return self._pub_key

    def priv_key(self):
        if not self.has_private_keys:
            raise ValueError('This Account object does not contain private keys')

        return Wallet.deserialize(self._priv_key, network=self._network).export_to_wif()

    def address(self):
        if not self._address:
            wallet = Wallet.deserialize(self._priv_key or self._pub_key, network=self._network)
            self._address = wallet.to_address()

        return self._address

if __name__ == '__main__':
    bitcoin = BitcoinAccount.generate()
    print(bitcoin)
    bitcoin.print_qrcode()
    bitcoin.encrypted_priv_key()

    print()

    ether = EthereumAccount.generate()
    print(ether)
    ether.print_qrcode()
    ether.encrypted_priv_key()
