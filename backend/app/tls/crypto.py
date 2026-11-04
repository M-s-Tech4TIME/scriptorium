"""Certificate generation, validation, SAN normalization, TLS context (0040).

Cryptographic profile (owner-approved F-B1/F-E1):

- local CA: ECDSA P-384, SHA-384, 10-year lifetime, CA path length 0;
- leaf: ECDSA P-256, SHA-256, 90-day lifetime, serverAuth EKU;
- TLS 1.2 minimum, TLS 1.3 enabled; TLS 1.2 is ECDHE + AEAD only;
- no CBC/RSA-key-exchange/3DES/RC4/NULL, no compression, no
  renegotiation, no session tickets.

Imported material is validated with the same strength rules before it is
installed. The chain is checked internally (leaf → intermediates), but
trust in an imported root remains the operator's responsibility.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_DAYS = 3650
LEAF_DAYS = 90
CA_KEY_SIZE = 384
LEAF_CURVE = ec.SECP256R1()

# TLS 1.2: ECDHE key exchange + AEAD only (F-E1). RSA suites are included
# for imported RSA certificates; no CBC, RSA-kex, 3DES, RC4, or NULL.
TLS12_CIPHERS = (
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256"
)


class TlsCryptoError(RuntimeError):
    """Certificate/key material is invalid or too weak."""


@dataclass(frozen=True)
class SubjectAltName:
    kind: Literal["DNS", "IP"]
    value: str

    @property
    def text(self) -> str:
        return f"{self.kind}:{self.value}"


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def normalize_dns(value: str) -> str:
    """Lowercase/IDNA-normalize a DNS name; wildcard only as leftmost label."""
    candidate = value.strip().rstrip(".")
    if not candidate:
        raise TlsCryptoError("A DNS name may not be empty.")
    wildcard = candidate.startswith("*.")
    if wildcard:
        candidate = candidate[2:]
        if "." not in candidate:
            raise TlsCryptoError("A wildcard name must have at least two labels.")
    if "*" in candidate:
        raise TlsCryptoError("A wildcard is only allowed as the leftmost label.")
    try:
        ascii_name = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise TlsCryptoError(f"Invalid DNS name {value!r}.") from exc
    ascii_name = ascii_name.lower()
    if len(ascii_name) > 253:
        raise TlsCryptoError("A DNS name may not exceed 253 characters.")
    labels = ascii_name.split(".")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not all(ch.isalnum() or ch == "-" for ch in label)
        for label in labels
    ):
        raise TlsCryptoError(f"Invalid DNS name {value!r}.")
    return f"*.{ascii_name}" if wildcard else ascii_name


def normalize_ip(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError as exc:
        raise TlsCryptoError(f"Invalid IP address {value!r}.") from exc


def parse_san(value: str) -> SubjectAltName:
    """Accept ``DNS:name``, ``IP:addr``, or a bare name/address."""
    raw = value.strip()
    if not raw:
        raise TlsCryptoError("A SAN may not be empty.")
    if ":" in raw:
        prefix, rest = raw.split(":", 1)
        kind = prefix.strip().upper()
        if kind in ("DNS", "IP"):
            raw = rest.strip()
            if kind == "IP":
                return SubjectAltName("IP", normalize_ip(raw))
            return SubjectAltName("DNS", normalize_dns(raw))
        # IPv6 without the IP: prefix (contains several colons).
        if raw.count(":") >= 2 and prefix.strip().isdigit():
            return SubjectAltName("IP", normalize_ip(raw))
    try:
        return SubjectAltName("IP", normalize_ip(raw))
    except TlsCryptoError:
        return SubjectAltName("DNS", normalize_dns(raw))


def parse_url_host(value: str) -> SubjectAltName:
    raw = value.strip()
    parts = urlsplit(raw if "://" in raw else f"//{raw}")
    if parts.username or parts.password:
        raise TlsCryptoError("A URL SAN may not contain credentials.")
    host = parts.hostname
    if not host:
        raise TlsCryptoError(f"URL {value!r} has no hostname.")
    try:
        return SubjectAltName("IP", normalize_ip(host))
    except TlsCryptoError:
        return SubjectAltName("DNS", normalize_dns(host))


def detect_sans(
    hostnames: list[str] | None = None,
    urls: list[str] | None = None,
    sans: list[str] | None = None,
) -> list[SubjectAltName]:
    """Auto-detect local names/addresses and add operator overrides (F-K1)."""
    found: dict[tuple[str, str], SubjectAltName] = {}

    def add(item: SubjectAltName) -> None:
        found[(item.kind, item.value)] = item

    for value in hostnames or []:
        add(parse_san(value))
    for value in urls or []:
        add(parse_url_host(value))
    for value in sans or []:
        add(parse_san(value))

    auto_hosts = ["localhost", socket.gethostname(), socket.getfqdn()]
    for host in auto_hosts:
        if not host:
            continue
        try:
            add(SubjectAltName("DNS", normalize_dns(host)))
        except TlsCryptoError:
            continue
    for host in auto_hosts:
        if not host:
            continue
        try:
            infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError:
            continue
        for info in infos:
            address = str(info[4][0])
            try:
                add(SubjectAltName("IP", normalize_ip(address)))
            except TlsCryptoError:
                continue
    for loopback in ("127.0.0.1", "::1"):
        add(SubjectAltName("IP", normalize_ip(loopback)))

    if not found:
        raise TlsCryptoError("No subject alternative names could be determined.")
    return sorted(found.values(), key=lambda item: (item.kind, item.value))


def build_san_extension(sans: list[SubjectAltName]) -> x509.SubjectAlternativeName:
    values: list[x509.GeneralName] = []
    for item in sans:
        if item.kind == "DNS":
            values.append(x509.DNSName(item.value))
        else:
            values.append(x509.IPAddress(ipaddress.ip_address(item.value)))
    if not values:
        raise TlsCryptoError("A certificate needs at least one SAN.")
    return x509.SubjectAlternativeName(values)


def _serial() -> int:
    # 128 random bits; never zero (RFC 5280).
    return uuid.uuid4().int & ((1 << 128) - 1) or 1


def generate_ca(
    common_name: str = "Scriptorium Local CA",
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = ec.generate_private_key(ec.SECP384R1())
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Scriptorium"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(_serial())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
            critical=False,
        )
        .sign(key, hashes.SHA384())
    )
    return key, cert


def generate_leaf(
    ca_key: ec.EllipticCurvePrivateKey,
    ca_cert: x509.Certificate,
    sans: list[SubjectAltName],
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = ec.generate_private_key(LEAF_CURVE)
    first = sans[0]
    common_name = first.value
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Scriptorium"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name[:64]),
        ]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(_serial())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=LEAF_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(build_san_extension(sans), critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                cast(ec.EllipticCurvePublicKey, ca_cert.public_key())
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def private_key_pem(key: object) -> bytes:
    if not isinstance(
        key,
        (
            ec.EllipticCurvePrivateKey,
            rsa.RSAPrivateKey,
            ed25519.Ed25519PrivateKey,
        ),
    ):
        raise TlsCryptoError("Unsupported private key type.")
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def cert_pem(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def load_cert_chain(path: Path) -> list[x509.Certificate]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TlsCryptoError(f"Cannot read certificate {path}: {exc}") from exc
    try:
        certs = x509.load_pem_x509_certificates(data)
    except ValueError as exc:
        raise TlsCryptoError(f"Certificate file {path} is not valid PEM.") from exc
    if not certs:
        raise TlsCryptoError(f"Certificate file {path} is empty.")
    return certs


def load_private_key(path: Path) -> object:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TlsCryptoError(f"Cannot read private key {path}: {exc}") from exc
    try:
        return serialization.load_pem_private_key(data, password=None)
    except (ValueError, TypeError) as exc:
        raise TlsCryptoError(f"Private key {path} is not valid PEM.") from exc


def _key_strength(key: object) -> str | None:
    if isinstance(key, rsa.RSAPrivateKey):
        if key.key_size < 2048:
            return f"RSA key is {key.key_size} bits; 2048+ is required."
        return None
    if isinstance(key, ec.EllipticCurvePrivateKey):
        if key.curve.key_size < 256:
            return f"ECDSA curve is {key.curve.name}; P-256+ is required."
        return None
    if isinstance(key, ed25519.Ed25519PrivateKey):
        return None
    return f"Unsupported private key type {type(key).__name__}."


def _signature_hash_ok(cert: x509.Certificate) -> bool:
    algorithm = cert.signature_hash_algorithm
    if algorithm is None:  # Ed25519/Ed448
        return True
    return isinstance(algorithm, (hashes.SHA256, hashes.SHA384, hashes.SHA512))


def _public_key_bytes(key: object) -> bytes:
    candidate = key
    public_key = getattr(key, "public_key", None)
    if callable(public_key):
        candidate = public_key()
    public_bytes = getattr(candidate, "public_bytes", None)
    if not callable(public_bytes):
        raise TlsCryptoError("Unsupported key object.")
    data = public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return bytes(data)


def sans_from_cert(cert: x509.Certificate) -> list[SubjectAltName]:
    try:
        extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return []
    values: list[SubjectAltName] = []
    for name in extension.value.get_values_for_type(x509.DNSName):
        values.append(SubjectAltName("DNS", str(name)))
    for address in extension.value.get_values_for_type(x509.IPAddress):
        values.append(SubjectAltName("IP", str(address)))
    return values


def validate_material(
    cert_chain: list[x509.Certificate],
    key: object,
    *,
    now: datetime | None = None,
    require_server_auth: bool = True,
    allow_ca: bool = False,
) -> list[str]:
    """Return validation errors; an empty list means the material is usable."""
    errors: list[str] = []
    if not cert_chain:
        return ["No certificate was supplied."]
    leaf = cert_chain[0]
    moment = now or datetime.now(UTC)
    if moment < _as_utc(leaf.not_valid_before_utc):
        errors.append("Leaf certificate is not valid yet.")
    if moment > _as_utc(leaf.not_valid_after_utc):
        errors.append("Leaf certificate has expired.")
    strength = _key_strength(key)
    if strength:
        errors.append(strength)
    try:
        if _public_key_bytes(key) != _public_key_bytes(leaf.public_key()):
            errors.append("Private key does not match the leaf certificate.")
    except TlsCryptoError as exc:
        errors.append(str(exc))
    if not _signature_hash_ok(leaf):
        errors.append("Leaf signature uses a hash weaker than SHA-256.")
    try:
        basic = leaf.extensions.get_extension_for_class(x509.BasicConstraints).value
        if basic.ca and not allow_ca:
            errors.append("Leaf certificate is a CA certificate.")
    except x509.ExtensionNotFound:
        pass
    if require_server_auth:
        try:
            eku = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
            if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
                errors.append("Leaf certificate lacks the serverAuth EKU.")
        except x509.ExtensionNotFound:
            errors.append("Leaf certificate lacks the serverAuth EKU.")
    if not allow_ca and not sans_from_cert(leaf):
        errors.append("Leaf certificate has no DNS/IP subject alternative names.")
    for index in range(len(cert_chain) - 1):
        try:
            cert_chain[index].verify_directly_issued_by(cert_chain[index + 1])
        except (ValueError, TypeError) as exc:
            errors.append(
                f"Certificate chain link {index} → {index + 1} is invalid: {exc}"
            )
    return errors


def cert_fingerprint(cert: x509.Certificate) -> str:
    return cert.fingerprint(hashes.SHA256()).hex()


def cert_days_left(cert: x509.Certificate, *, now: datetime | None = None) -> int:
    moment = now or datetime.now(UTC)
    return max(
        0, int((_as_utc(cert.not_valid_after_utc) - moment).total_seconds() // 86400)
    )


def cert_subject(cert: x509.Certificate) -> str:
    return cert.subject.rfc4514_string()


def cert_issuer(cert: x509.Certificate) -> str:
    return cert.issuer.rfc4514_string()


def cert_common_name(cert: x509.Certificate) -> str:
    values = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    return str(values[0].value) if values else ""


def host_allowed(host: str, sans: list[SubjectAltName]) -> bool:
    """Match a redirect Host against the current certificate SANs."""
    candidate = host.strip().strip("[]").rstrip(".").lower()
    if not candidate:
        return False
    try:
        candidate_ip = str(ipaddress.ip_address(candidate))
    except ValueError:
        candidate_ip = ""
    for item in sans:
        if item.kind == "IP" and candidate_ip and item.value == candidate_ip:
            return True
        if item.kind == "DNS":
            if item.value == candidate:
                return True
            if item.value.startswith("*."):
                suffix = item.value[2:]
                if candidate.endswith(f".{suffix}") and candidate.count(".") == (
                    suffix.count(".") + 1
                ):
                    return True
    return False


def create_server_context(certfile: Path, keyfile: Path) -> ssl.SSLContext:
    """Build the hardened server context used by the web worker (F-E1)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_ciphers(TLS12_CIPHERS)
    context.options |= (
        ssl.OP_NO_COMPRESSION
        | ssl.OP_NO_RENEGOTIATION
        | ssl.OP_NO_TICKET
        | ssl.OP_CIPHER_SERVER_PREFERENCE
    )
    context.post_handshake_auth = False
    context.num_tickets = 0  # TLS 1.3 session tickets off (F-E1)
    context.load_cert_chain(str(certfile), str(keyfile))
    return context
