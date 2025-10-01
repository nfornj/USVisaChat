"""
MongoDB Certificate Validation Utility
Validates X.509 certificates for MongoDB Atlas authentication
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


class CertificateValidator:
    """Validates X.509 certificates for MongoDB authentication"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_certificate_file(self, cert_path: str) -> Tuple[bool, Dict]:
        """
        Validate a certificate file
        
        Args:
            cert_path: Path to certificate file (.pem)
        
        Returns:
            Tuple[bool, Dict]: (is_valid, certificate_info)
        """
        self.errors = []
        self.warnings = []
        
        # Check if file exists
        if not os.path.exists(cert_path):
            self.errors.append(f"Certificate file not found: {cert_path}")
            return False, {}
        
        # Check file permissions (should not be world-readable)
        try:
            file_stat = os.stat(cert_path)
            if file_stat.st_mode & 0o004:  # World-readable
                self.warnings.append(
                    f"Certificate file is world-readable. "
                    f"Consider: chmod 600 {cert_path}"
                )
        except Exception as e:
            self.warnings.append(f"Could not check file permissions: {e}")
        
        # Read and parse certificate
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            # Try to load as PEM certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Extract certificate information
            cert_info = self._extract_certificate_info(cert)
            
            # Validate certificate
            is_valid = self._validate_certificate_properties(cert, cert_info)
            
            return is_valid, cert_info
            
        except Exception as e:
            self.errors.append(f"Failed to parse certificate: {e}")
            return False, {}
    
    def _extract_certificate_info(self, cert: x509.Certificate) -> Dict:
        """Extract information from certificate"""
        info = {
            'subject': {},
            'issuer': {},
            'valid_from': cert.not_valid_before,
            'valid_until': cert.not_valid_after,
            'serial_number': cert.serial_number,
            'version': cert.version.name,
            'signature_algorithm': cert.signature_algorithm_oid._name,
            'extensions': []
        }
        
        # Extract subject information
        for attribute in cert.subject:
            info['subject'][attribute.oid._name] = attribute.value
        
        # Extract issuer information
        for attribute in cert.issuer:
            info['issuer'][attribute.oid._name] = attribute.value
        
        # Extract extensions
        try:
            for ext in cert.extensions:
                info['extensions'].append({
                    'oid': ext.oid._name,
                    'critical': ext.critical,
                    'value': str(ext.value)
                })
        except Exception as e:
            logger.warning(f"Could not extract extensions: {e}")
        
        return info
    
    def _validate_certificate_properties(
        self, 
        cert: x509.Certificate, 
        cert_info: Dict
    ) -> bool:
        """Validate certificate properties"""
        is_valid = True
        now = datetime.utcnow()
        
        # Check if certificate is expired
        if cert_info['valid_until'] < now:
            self.errors.append(
                f"Certificate expired on {cert_info['valid_until']}"
            )
            is_valid = False
        
        # Check if certificate is not yet valid
        if cert_info['valid_from'] > now:
            self.errors.append(
                f"Certificate not valid until {cert_info['valid_from']}"
            )
            is_valid = False
        
        # Warn if certificate expires soon (within 30 days)
        days_until_expiry = (cert_info['valid_until'] - now).days
        if days_until_expiry < 30 and days_until_expiry > 0:
            self.warnings.append(
                f"Certificate expires in {days_until_expiry} days"
            )
        
        # Check if subject CN is present (required for MongoDB X.509)
        if 'commonName' not in cert_info['subject']:
            self.errors.append(
                "Certificate missing Common Name (CN) in subject - "
                "required for MongoDB X.509 authentication"
            )
            is_valid = False
        
        return is_valid
    
    def validate_ca_certificate(self, ca_cert_path: str) -> Tuple[bool, Dict]:
        """
        Validate a CA certificate file
        
        Args:
            ca_cert_path: Path to CA certificate file
        
        Returns:
            Tuple[bool, Dict]: (is_valid, ca_cert_info)
        """
        is_valid, cert_info = self.validate_certificate_file(ca_cert_path)
        
        if is_valid:
            # Additional checks for CA certificate
            try:
                with open(ca_cert_path, 'rb') as f:
                    cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                
                # Check if this is a CA certificate
                try:
                    basic_constraints = cert.extensions.get_extension_for_oid(
                        x509.oid.ExtensionOID.BASIC_CONSTRAINTS
                    )
                    if not basic_constraints.value.ca:
                        self.warnings.append(
                            "Certificate does not have CA flag set - "
                            "this may not be a valid CA certificate"
                        )
                except x509.ExtensionNotFound:
                    self.warnings.append(
                        "Certificate missing Basic Constraints extension"
                    )
            except Exception as e:
                self.warnings.append(f"Could not validate CA properties: {e}")
        
        return is_valid, cert_info
    
    def print_validation_results(self):
        """Print validation results"""
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Certificate validation passed with no issues")
    
    def print_certificate_info(self, cert_info: Dict):
        """Print certificate information"""
        if not cert_info:
            return
        
        print("\n📜 CERTIFICATE INFORMATION:")
        print(f"   Subject: {cert_info.get('subject', {})}")
        print(f"   Issuer: {cert_info.get('issuer', {})}")
        print(f"   Valid From: {cert_info.get('valid_from')}")
        print(f"   Valid Until: {cert_info.get('valid_until')}")
        print(f"   Serial Number: {cert_info.get('serial_number')}")
        print(f"   Version: {cert_info.get('version')}")
        print(f"   Signature Algorithm: {cert_info.get('signature_algorithm')}")
        
        if cert_info.get('extensions'):
            print(f"   Extensions: {len(cert_info['extensions'])} found")


def validate_mongodb_certificates(
    client_cert_path: Optional[str] = None,
    ca_cert_path: Optional[str] = None
) -> bool:
    """
    Validate MongoDB certificates from environment or provided paths
    
    Args:
        client_cert_path: Path to client certificate (optional)
        ca_cert_path: Path to CA certificate (optional)
    
    Returns:
        bool: True if all provided certificates are valid
    """
    validator = CertificateValidator()
    all_valid = True
    
    # Get paths from environment if not provided
    if not client_cert_path:
        client_cert_path = os.getenv("MONGODB_TLS_CERT_FILE")
    if not ca_cert_path:
        ca_cert_path = os.getenv("MONGODB_TLS_CA_FILE")
    
    print("="*70)
    print("🔐 MONGODB CERTIFICATE VALIDATION")
    print("="*70)
    
    # Validate client certificate
    if client_cert_path:
        print(f"\n📋 Validating Client Certificate: {client_cert_path}")
        is_valid, cert_info = validator.validate_certificate_file(client_cert_path)
        validator.print_certificate_info(cert_info)
        validator.print_validation_results()
        all_valid = all_valid and is_valid
    else:
        print("\n⚠️  No client certificate specified (MONGODB_TLS_CERT_FILE)")
    
    # Validate CA certificate
    if ca_cert_path:
        print(f"\n📋 Validating CA Certificate: {ca_cert_path}")
        is_valid, ca_info = validator.validate_ca_certificate(ca_cert_path)
        validator.print_certificate_info(ca_info)
        validator.print_validation_results()
        all_valid = all_valid and is_valid
    else:
        print("\n⚠️  No CA certificate specified (MONGODB_TLS_CA_FILE)")
    
    print("\n" + "="*70)
    if all_valid:
        print("✅ ALL CERTIFICATES VALID")
    else:
        print("❌ CERTIFICATE VALIDATION FAILED")
    print("="*70 + "\n")
    
    return all_valid


if __name__ == "__main__":
    """Run certificate validation"""
    from dotenv import load_dotenv
    load_dotenv()
    
    import sys
    
    # Allow command-line arguments
    client_cert = sys.argv[1] if len(sys.argv) > 1 else None
    ca_cert = sys.argv[2] if len(sys.argv) > 2 else None
    
    validate_mongodb_certificates(client_cert, ca_cert)




