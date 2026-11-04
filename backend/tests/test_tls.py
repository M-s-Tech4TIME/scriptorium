"""Built-in TLS lifecycle regressions (decision 0040)."""

from __future__ import annotations

import ipaddress
import os
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.tls import (
    TlsError,
    generate,
    history,
    hsts,
    import_pair,
    prune,
    renew,
    rollback,
    status,
    verify,
)
from app.tls.crypto import (
    TLS12_CIPHERS,
    TlsCryptoError,
    create_server_context,
    normalize_dns,
    normalize_ip,
    parse_san,
    parse_url_host,
    validate_material,
)
from app.tls.manager import redirect_target
from app.tls.state import (
    ca_cert_path,
    ca_key_path,
    cert_path,
    key_path,
    read_state,
    state_path,
)


@pytest.fixture(autouse=True)
def _tls_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "tls"
    monkeypatch.setenv("SC_TLS_ROOT", str(root))
    monkeypatch.delenv("SC_TLS_CERT", raising=False)
    monkeypatch.delenv("SC_TLS_KEY", raising=False)
    monkeypatch.delenv("SC_TLS_REDIRECT_HOST", raising=False)
    monkeypatch.delenv("SC_TLS_HSTS_MAX_AGE", raising=False)


def _self_signed(
    *,
    common_name: str = "import.test",
    sans: list[x509.GeneralName] | None = None,
    days: int = 30,
    key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None = None,
    ca: bool = False,
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey]:
    private_key = key or ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(UTC)
    if days < 0:
        not_before = now - timedelta(days=2)
        not_after = now - timedelta(days=1)
    else:
        not_before = now - timedelta(minutes=1)
        not_after = now + timedelta(days=days)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if not ca:
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        ).add_extension(
            x509.SubjectAlternativeName(
                sans
                or [
                    x509.DNSName("import.test"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
    return builder.sign(private_key, hashes.SHA256()), private_key


def _write_pair(
    directory: Path,
    cert: x509.Certificate,
    key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey,
) -> tuple[Path, Path]:
    cert_file = directory / "fullchain.pem"
    key_file = directory / "privkey.pem"
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_file, key_file


def test_generate_status_verify_and_context() -> None:
    result = generate(
        hostnames=["example.test"],
        urls=["https://www.example.test/docs"],
        sans=["IP:192.0.2.10"],
        reload_service=False,
    )
    assert result.configured is True
    assert result.mode == "generated"
    assert 88 <= result.days_left <= 90
    assert "DNS:example.test" in result.sans
    assert "DNS:www.example.test" in result.sans
    assert "IP:192.0.2.10" in result.sans
    assert result.fingerprint_sha256
    assert verify() == []
    assert cert_path().is_file()
    assert key_path().is_file()
    assert ca_cert_path().is_file()
    assert ca_key_path().is_file()
    assert (key_path().stat().st_mode & 0o777) == 0o600
    assert (cert_path().stat().st_mode & 0o777) == 0o644
    assert (ca_key_path().stat().st_mode & 0o777) == 0o600

    context = create_server_context(cert_path(), key_path())
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_3
    assert context.num_tickets == 0
    names = {cipher["name"] for cipher in context.get_ciphers()}
    for cipher in TLS12_CIPHERS.split(":"):
        assert cipher in names
    tls12 = {
        cipher["name"]
        for cipher in context.get_ciphers()
        if cipher["protocol"] == "TLSv1.2"
    }
    assert all(name.startswith("ECDHE-") for name in tls12)
    assert not any(
        token in name for name in names for token in ("CBC", "RC4", "3DES", "NULL")
    )


def test_renew_rollback_prune_and_history() -> None:
    first = generate(hostnames=["example.test"], reload_service=False)
    first_version = first.version
    renewed = renew(force=True, reload_service=False)
    assert renewed.renewed is True
    assert renewed.status is not None
    assert renewed.status.version != first_version
    second_version = renewed.status.version
    third = renew(force=True, reload_service=False)
    assert third.status is not None
    third_version = third.status.version

    restored = rollback(version=first_version, reload_service=False)
    assert restored.version == first_version
    assert status().version == first_version

    # keep=1 protects both the active version and the newest version.
    removed = prune(keep=1)
    assert removed == [second_version]
    assert [row["version"] for row in history()] == [
        third_version,
        first_version,
    ]


def test_renew_respects_imported_mode(tmp_path: Path) -> None:
    cert, key = _self_signed()
    cert_file, key_file = _write_pair(tmp_path, cert, key)
    result = import_pair(cert_file, key_file, reload_service=False)
    assert result.status.mode == "imported"
    assert result.status.sans == ["DNS:import.test", "IP:127.0.0.1"]
    outcome = renew(force=True, reload_service=False)
    assert outcome.renewed is False
    assert "imported" in outcome.reason


def test_import_rejects_mismatched_key(tmp_path: Path) -> None:
    cert, _ = _self_signed()
    other_key = ec.generate_private_key(ec.SECP256R1())
    cert_file, key_file = _write_pair(tmp_path, cert, other_key)
    with pytest.raises(TlsError, match="does not match"):
        import_pair(cert_file, key_file, reload_service=False)


def test_validation_rejects_expired_weak_and_unsigned_material() -> None:
    expired_cert, expired_key = _self_signed(days=-1)
    errors = validate_material([expired_cert], expired_key)
    assert any("expired" in error for error in errors)

    weak_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    weak_cert, _ = _self_signed(key=weak_key)
    errors = validate_material([weak_cert], weak_key)
    assert any("2048" in error for error in errors)

    cert, key = _self_signed()
    errors = validate_material([cert], key, require_server_auth=False)
    assert errors == []


def test_san_normalization_and_parsing() -> None:
    assert normalize_dns("ExAmPle.COM.") == "example.com"
    assert normalize_dns("*.Example.COM") == "*.example.com"
    assert normalize_dns("bücher.example") == "xn--bcher-kva.example"
    with pytest.raises(TlsCryptoError):
        normalize_dns("*.*.example")
    assert normalize_ip("[::1]") == "::1"
    assert normalize_ip("192.0.2.1") == "192.0.2.1"
    assert parse_san("DNS:Example.COM").text == "DNS:example.com"
    assert parse_san("IP:2001:db8::1").text == "IP:2001:db8::1"
    assert parse_san("2001:db8::1").text == "IP:2001:db8::1"
    assert parse_url_host("https://Example.COM:8443/path").text == "DNS:example.com"
    assert parse_url_host("https://[2001:db8::1]/").text == "IP:2001:db8::1"


def test_redirect_host_is_san_limited() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    assert redirect_target("example.test:80") == "example.test"
    assert redirect_target("evil.test:80") == "example.test"
    assert redirect_target("[::1]:80") == "::1"

    os.environ["SC_TLS_REDIRECT_HOST"] = "canonical.example"
    try:
        assert redirect_target("evil.test") == "canonical.example"
    finally:
        del os.environ["SC_TLS_REDIRECT_HOST"]


def test_hsts_is_off_by_default_and_persists() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    assert read_state().hsts is False
    assert status().hsts is False
    enabled = hsts(True, max_age=600)
    assert enabled.hsts is True
    assert enabled.hsts_max_age == 600
    assert state_path().is_file()
    disabled = hsts(False)
    assert disabled.hsts is False


def test_failed_reload_restores_previous_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = generate(hostnames=["example.test"], reload_service=False)

    def _fail() -> tuple[bool, str]:
        return False, "unit test reload failure"

    monkeypatch.setattr("app.tls.manager.reload_web", _fail)
    with pytest.raises(TlsError, match="previous certificate was restored"):
        generate(hostnames=["example.test"], reload_service=True)
    current = status()
    assert current.version == first.version
    assert current.configured is True
    assert read_state().version == first.version


def test_verify_reports_missing_material(tmp_path: Path) -> None:
    # No generation has happened in this test's root.
    findings = verify()
    assert any(finding.level == "error" for finding in findings)
    assert not (tmp_path / "tls" / "current").exists()
