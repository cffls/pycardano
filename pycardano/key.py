from __future__ import annotations

import json

from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from nacl.public import PrivateKey
from nacl.signing import SigningKey as NACLSigningKey

from pycardano.exception import InvalidKeyTypeException
from pycardano.hash import AddrKeyHash, ADDR_KEYHASH_SIZE
from pycardano.serialization import CBORSerializable


class Key(CBORSerializable):
    """A class that holds a cryptographic key and some metadata. e.g. signing key, verification key."""
    KEY_TYPE = ""
    DESCRIPTION = ""

    def __init__(self, payload: bytes, key_type: str = None, description: str = None):
        self._payload = payload
        self._key_type = key_type or self.KEY_TYPE
        self._description = description or self.KEY_TYPE

    @property
    def payload(self) -> bytes:
        return self._payload

    @property
    def key_type(self) -> str:
        return self._key_type

    @property
    def description(self) -> str:
        return self._description

    def serialize(self) -> bytes:
        return self.payload

    @classmethod
    def deserialize(cls, value: bytes) -> Key:
        return cls(value)

    def to_json(self) -> str:
        """Serialize the key to JSON.

        The json output has three fields: "type", "description", and "cborHex".

        Returns:
            str: JSON representation of the key.
        """
        return json.dumps({
            "type": self.key_type,
            "description": self.description,
            "cborHex": self.to_cbor()
        })

    @classmethod
    def from_json(cls, data: str, validate_type=False) -> Key:
        """Restore a key from a JSON string.

        Args:
            data (str): JSON string.
            validate_type (bool): Checks whether the type specified in json object is the same
                as the class's default type.

        Returns:
            Key: The key restored from JSON.

        Raises:
            InvalidKeyTypeException: When `validate_type=True` and the type in json is not equal to the default type
                of the Key class used.
        """
        obj = json.loads(data)

        if validate_type and obj["type"] != cls.KEY_TYPE:
            raise InvalidKeyTypeException(f"Expect key type: {cls.KEY_TYPE}, got {obj['type']} instead.")

        return cls(cls.from_cbor(obj["cborHex"]).payload,
                   key_type=obj["type"],
                   description=obj["description"])

    def __eq__(self, other):
        if not isinstance(other, Key):
            return False
        else:
            return self.payload == other.payload and self.description == other.description and \
                self.key_type == other.key_type

    def __repr__(self) -> str:
        return self.to_json()


class AddressKey(Key):
    def hash(self) -> AddrKeyHash:
        """Compute a blake2b hash from the key

        Args:
            hash_size: Size of the hash output in bytes.

        Returns:
            AddrKeyHash: Hash output in bytes.
        """
        return AddrKeyHash(blake2b(self.payload, ADDR_KEYHASH_SIZE, encoder=RawEncoder))


class SigningKey(Key):

    def sign(self, data: bytes) -> bytes:
        signed_message = NACLSigningKey(self.payload).sign(data)
        return signed_message.signature


class PaymentSigningKey(SigningKey):
    KEY_TYPE = "PaymentSigningKeyShelley_ed25519"
    DESCRIPTION = "Payment Verification Key"


class PaymentVerificationKey(AddressKey):
    KEY_TYPE = "PaymentVerificationKeyShelley_ed25519"
    DESCRIPTION = "Payment Verification Key"


class PaymentKeyPair:
    def __init__(self, signing_key: bytes, verification_key: bytes):
        self.signing_key = PaymentSigningKey(signing_key)
        self.verification_key = PaymentVerificationKey(verification_key)

    @classmethod
    def generate(cls) -> PaymentKeyPair:
        signing_key = PrivateKey.generate()
        return cls.from_private_key(bytes(signing_key))

    @classmethod
    def from_private_key(cls, signing_key: bytes) -> PaymentKeyPair:
        verification_key = NACLSigningKey(bytes(signing_key)).verify_key
        return cls(signing_key, bytes(verification_key))


class StakeSigningKey(SigningKey):
    KEY_TYPE = "StakeSigningKeyShelley_ed25519"
    DESCRIPTION = "Stake Verification Key"


class StakeVerificationKey(AddressKey):
    KEY_TYPE = "StakeVerificationKeyShelley_ed25519"
    DESCRIPTION = "Stake Verification Key"


class StakeKeyPair:
    def __init__(self, signing_key: bytes, verification_key: bytes):
        self.signing_key = StakeSigningKey(signing_key)
        self.verification_key = StakeVerificationKey(verification_key)

    @classmethod
    def generate(cls) -> StakeKeyPair:
        signing_key = PrivateKey.generate()
        return cls.from_private_key(bytes(signing_key))

    @classmethod
    def from_private_key(cls, signing_key: bytes) -> StakeKeyPair:
        verification_key = NACLSigningKey(bytes(signing_key)).verify_key
        return cls(signing_key, bytes(verification_key))