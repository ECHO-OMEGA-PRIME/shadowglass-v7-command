"""
PIE SIGNED MANIFEST VERIFIER
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

REQUIRE SIGNED ARTIFACT MANIFESTS.
Verify sha256 against manifest.
Reject on mismatch.
"""

import json
import hashlib
import hmac
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime
from loguru import logger


class ManifestResult(Enum):
    """Manifest verification result codes."""
    VALID = "VALID"
    MISSING_MANIFEST = "MISSING_MANIFEST"
    INVALID_MANIFEST_FORMAT = "INVALID_MANIFEST_FORMAT"
    MISSING_SIGNATURE = "MISSING_SIGNATURE"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass
class ArtifactManifest:
    """Signed artifact manifest structure."""
    artifact_id: str
    artifact_type: str
    sha256_hash: str
    file_size: int
    created_at: str
    signed_by: str
    signature: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ManifestVerification:
    """Manifest verification result."""
    artifact_path: str
    manifest_path: str
    valid: bool
    result: ManifestResult
    manifest: Optional[ArtifactManifest] = None
    computed_hash: Optional[str] = None
    error_detail: Optional[str] = None


class PIEManifestVerifier:
    """
    Signed manifest verifier for PIE artifacts.

    SECURITY PROPERTIES:
    - REQUIRE signed manifests
    - Verify SHA-256 hash
    - Verify manifest signature
    - FAIL CLOSED on any error
    """

    REQUIRED_MANIFEST_FIELDS = [
        "artifact_id",
        "artifact_type",
        "sha256_hash",
        "file_size",
        "created_at",
        "signed_by",
        "signature",
    ]

    def __init__(self, signing_key: bytes):
        """
        Initialize manifest verifier with signing key.

        Args:
            signing_key: HMAC signing key for manifest verification

        Raises:
            ValueError: If signing key is missing or too short
        """
        if not signing_key or len(signing_key) < 32:
            raise ValueError(
                "Manifest verifier requires signing key (min 32 bytes). "
                "No default key. FAIL CLOSED."
            )

        self._signing_key = signing_key
        logger.info("PIE Manifest Verifier initialized")

    def verify(
        self,
        artifact_path: str,
        manifest_path: Optional[str] = None
    ) -> ManifestVerification:
        """
        Verify an artifact against its signed manifest.

        FAIL CLOSED: Any verification error returns invalid result.

        Args:
            artifact_path: Path to the artifact file
            manifest_path: Path to manifest (defaults to artifact_path + .manifest.json)

        Returns:
            ManifestVerification with result
        """
        # Determine manifest path
        if manifest_path is None:
            manifest_path = f"{artifact_path}.manifest.json"

        # Check artifact exists
        artifact_file = Path(artifact_path)
        if not artifact_file.exists():
            logger.warning(f"MANIFEST_REJECT: Artifact not found: {artifact_path}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.ARTIFACT_NOT_FOUND
            )

        # Check manifest exists
        manifest_file = Path(manifest_path)
        if not manifest_file.exists():
            logger.warning(f"MANIFEST_REJECT: Manifest not found: {manifest_path}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.MISSING_MANIFEST
            )

        # Load manifest
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"MANIFEST_REJECT: Invalid JSON: {e}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.INVALID_MANIFEST_FORMAT,
                error_detail=str(e)
            )
        except Exception as e:
            logger.error(f"MANIFEST_REJECT: Failed to read manifest: {e}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.FAIL_CLOSED,
                error_detail=str(e)
            )

        # Validate required fields
        for field_name in self.REQUIRED_MANIFEST_FIELDS:
            if field_name not in manifest_data:
                logger.warning(
                    f"MANIFEST_REJECT: Missing required field: {field_name}"
                )
                return ManifestVerification(
                    artifact_path=artifact_path,
                    manifest_path=manifest_path,
                    valid=False,
                    result=ManifestResult.MISSING_REQUIRED_FIELD,
                    error_detail=f"Missing field: {field_name}"
                )

        # Parse manifest
        try:
            manifest = ArtifactManifest(
                artifact_id=manifest_data["artifact_id"],
                artifact_type=manifest_data["artifact_type"],
                sha256_hash=manifest_data["sha256_hash"],
                file_size=manifest_data["file_size"],
                created_at=manifest_data["created_at"],
                signed_by=manifest_data["signed_by"],
                signature=manifest_data["signature"],
                metadata=manifest_data.get("metadata", {})
            )
        except Exception as e:
            logger.warning(f"MANIFEST_REJECT: Failed to parse manifest: {e}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.INVALID_MANIFEST_FORMAT,
                error_detail=str(e)
            )

        # Verify manifest signature
        if not self._verify_signature(manifest):
            logger.warning(
                f"MANIFEST_REJECT: Invalid signature for {manifest.artifact_id}"
            )
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.INVALID_SIGNATURE,
                manifest=manifest
            )

        # Compute artifact hash
        try:
            computed_hash = self._compute_file_hash(artifact_file)
        except Exception as e:
            logger.error(f"MANIFEST_REJECT: Failed to compute hash: {e}")
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.FAIL_CLOSED,
                manifest=manifest,
                error_detail=str(e)
            )

        # Verify hash matches manifest
        if computed_hash != manifest.sha256_hash:
            logger.warning(
                f"MANIFEST_REJECT: Hash mismatch for {manifest.artifact_id}. "
                f"Expected: {manifest.sha256_hash}, Got: {computed_hash}"
            )
            return ManifestVerification(
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                valid=False,
                result=ManifestResult.HASH_MISMATCH,
                manifest=manifest,
                computed_hash=computed_hash
            )

        # VALID
        logger.info(
            f"MANIFEST_VALID: {manifest.artifact_id} "
            f"(hash: {computed_hash[:16]}...)"
        )
        return ManifestVerification(
            artifact_path=artifact_path,
            manifest_path=manifest_path,
            valid=True,
            result=ManifestResult.VALID,
            manifest=manifest,
            computed_hash=computed_hash
        )

    def _verify_signature(self, manifest: ArtifactManifest) -> bool:
        """
        Verify manifest signature.

        Signature covers: artifact_id:artifact_type:sha256_hash:file_size:created_at:signed_by
        """
        message = (
            f"{manifest.artifact_id}:"
            f"{manifest.artifact_type}:"
            f"{manifest.sha256_hash}:"
            f"{manifest.file_size}:"
            f"{manifest.created_at}:"
            f"{manifest.signed_by}"
        ).encode("utf-8")

        expected_signature = hmac.new(
            self._signing_key,
            message,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(manifest.signature, expected_signature)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_manifest(
        self,
        artifact_path: str,
        artifact_id: str,
        artifact_type: str,
        signed_by: str,
        metadata: Optional[dict] = None
    ) -> ArtifactManifest:
        """
        Create a signed manifest for an artifact.

        For internal/testing use only.

        Args:
            artifact_path: Path to artifact file
            artifact_id: Unique artifact identifier
            artifact_type: Artifact type (from canonical list)
            signed_by: Signer identifier
            metadata: Optional additional metadata

        Returns:
            Signed ArtifactManifest
        """
        artifact_file = Path(artifact_path)
        if not artifact_file.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        # Compute hash
        sha256_hash = self._compute_file_hash(artifact_file)

        # Get file size
        file_size = artifact_file.stat().st_size

        # Timestamp
        created_at = datetime.utcnow().isoformat() + "Z"

        # Compute signature
        message = (
            f"{artifact_id}:"
            f"{artifact_type}:"
            f"{sha256_hash}:"
            f"{file_size}:"
            f"{created_at}:"
            f"{signed_by}"
        ).encode("utf-8")

        signature = hmac.new(
            self._signing_key,
            message,
            hashlib.sha256
        ).hexdigest()

        return ArtifactManifest(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            sha256_hash=sha256_hash,
            file_size=file_size,
            created_at=created_at,
            signed_by=signed_by,
            signature=signature,
            metadata=metadata or {}
        )

    def save_manifest(self, manifest: ArtifactManifest, path: str) -> None:
        """Save manifest to JSON file."""
        manifest_dict = {
            "artifact_id": manifest.artifact_id,
            "artifact_type": manifest.artifact_type,
            "sha256_hash": manifest.sha256_hash,
            "file_size": manifest.file_size,
            "created_at": manifest.created_at,
            "signed_by": manifest.signed_by,
            "signature": manifest.signature,
            "metadata": manifest.metadata,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=2)


def create_manifest_verifier(
    signing_key: Optional[bytes] = None
) -> PIEManifestVerifier:
    """
    Factory function for creating manifest verifier.

    FAIL CLOSED: If no signing key provided, raises ValueError.

    Args:
        signing_key: HMAC signing key

    Returns:
        Configured PIEManifestVerifier

    Raises:
        ValueError: If signing key is missing
    """
    if not signing_key:
        raise ValueError(
            "PIE Manifest Verifier requires signing_key. "
            "No default key. No bypass. FAIL CLOSED."
        )

    return PIEManifestVerifier(signing_key)
