# MongoDB X.509 Certificate Authentication Setup Guide

Complete guide for setting up certificate-based authentication with MongoDB Atlas.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Option 1: MongoDB Atlas Managed Certificates](#option-1-mongodb-atlas-managed-certificates-recommended)
4. [Option 2: Self-Signed Certificates](#option-2-self-signed-certificates-development-only)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**X.509 Certificate Authentication** provides enhanced security by:

- ✅ Eliminating password-based authentication
- ✅ Using cryptographic certificates for identity verification
- ✅ Enabling mutual TLS (mTLS) for encrypted connections
- ✅ Supporting certificate rotation and revocation

---

## 📦 Prerequisites

1. **MongoDB Atlas Account** (M10+ tier for X.509 support)
2. **OpenSSL** (for certificate generation)
3. **Python 3.8+** with dependencies:
   ```bash
   uv add pymongo dnspython cryptography
   ```

---

## 🔐 Option 1: MongoDB Atlas Managed Certificates (Recommended)

### Step 1: Enable X.509 Authentication in Atlas

1. **Log in to MongoDB Atlas**

   ```
   https://cloud.mongodb.com
   ```

2. **Navigate to Database Access**

   - Go to: Security → Database Access
   - Click "Add New Database User"

3. **Configure X.509 Authentication**
   - Choose "Certificate" as authentication method
   - Enter the certificate subject (CN/OU/O)
   - Grant appropriate roles (e.g., `readWrite@visa_community`)
   - Click "Add User"

### Step 2: Generate Client Certificate

MongoDB Atlas will provide you with a certificate subject format like:

```
CN=myuser,OU=myorg,O=MyCompany
```

Generate your client certificate:

```bash
# Create directory for certificates
mkdir -p ~/mongodb_certs
cd ~/mongodb_certs

# Generate private key
openssl genrsa -out client-key.pem 2048

# Create certificate signing request (CSR)
openssl req -new -key client-key.pem -out client-csr.pem \
  -subj "/CN=myuser/OU=myorg/O=MyCompany"

# Self-sign the certificate (valid for 365 days)
openssl x509 -req -in client-csr.pem -signkey client-key.pem \
  -out client-cert.pem -days 365

# Combine certificate and key into single PEM file
cat client-cert.pem client-key.pem > mongodb-client.pem

# Set proper permissions
chmod 600 mongodb-client.pem
```

### Step 3: Download Atlas CA Certificate

1. **Get CA Bundle from Atlas**

   - Go to: Clusters → Connect → Connect with Certificate
   - Download the CA certificate bundle
   - Save as `atlas-ca.pem`

2. **Or download from MongoDB directly:**
   ```bash
   curl -o atlas-ca.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
   ```

### Step 4: Configure Environment

Update your `.env` file:

```bash
# MongoDB Atlas with X.509
MONGODB_URI=mongodb+srv://cluster0.xxxxx.mongodb.net/
MONGODB_DATABASE=visa_community
MONGODB_AUTH_MECHANISM=MONGODB-X509

# Certificate paths
MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=/Users/yourname/mongodb_certs/mongodb-client.pem
MONGODB_TLS_CA_FILE=/Users/yourname/mongodb_certs/atlas-ca.pem
```

---

## 🛠️ Option 2: Self-Signed Certificates (Development Only)

**⚠️ Warning:** Self-signed certificates should ONLY be used for development/testing.

### Step 1: Generate CA Certificate

```bash
# Create certificates directory
mkdir -p ~/mongodb_certs
cd ~/mongodb_certs

# Generate CA private key
openssl genrsa -out ca-key.pem 4096

# Generate CA certificate (valid for 3650 days = 10 years)
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/CN=MongoDB CA/OU=Dev/O=YourCompany"
```

### Step 2: Generate Client Certificate

```bash
# Generate client private key
openssl genrsa -out client-key.pem 2048

# Generate client CSR
openssl req -new -key client-key.pem -out client-csr.pem \
  -subj "/CN=visa-app-client/OU=Development/O=YourCompany"

# Sign client certificate with CA
openssl x509 -req -in client-csr.pem -CA ca-cert.pem \
  -CAkey ca-key.pem -CAcreateserial -out client-cert.pem -days 365

# Combine client cert and key
cat client-cert.pem client-key.pem > mongodb-client.pem

# Set permissions
chmod 600 mongodb-client.pem
chmod 600 ca-key.pem
```

### Step 3: Configure for Self-Hosted MongoDB

```bash
# .env configuration
MONGODB_URI=mongodb://your-server.com:27017/
MONGODB_DATABASE=visa_community
MONGODB_AUTH_MECHANISM=MONGODB-X509

MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=/Users/yourname/mongodb_certs/mongodb-client.pem
MONGODB_TLS_CA_FILE=/Users/yourname/mongodb_certs/ca-cert.pem
```

---

## ⚙️ Configuration

### Complete .env Example

```bash
# MongoDB Atlas with X.509 Certificate Authentication
MONGODB_URI=mongodb+srv://cluster0.xxxxx.mongodb.net/
MONGODB_DATABASE=visa_community
MONGODB_AUTH_MECHANISM=MONGODB-X509

# TLS/Certificate Configuration
MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=/Users/neekrish/mongodb_certs/mongodb-client.pem
MONGODB_TLS_CA_FILE=/Users/neekrish/mongodb_certs/atlas-ca.pem

# Optional: Connection Pool Settings
MONGODB_MAX_POOL_SIZE=100
MONGODB_MIN_POOL_SIZE=10
```

### Environment Variable Reference

| Variable                 | Description             | Required | Default          |
| ------------------------ | ----------------------- | -------- | ---------------- |
| `MONGODB_URI`            | Full connection string  | Yes      | -                |
| `MONGODB_DATABASE`       | Database name           | Yes      | `visa_community` |
| `MONGODB_AUTH_MECHANISM` | Auth method             | Yes      | `SCRAM-SHA-256`  |
| `MONGODB_TLS_ENABLED`    | Enable TLS              | No       | `true`           |
| `MONGODB_TLS_CERT_FILE`  | Client certificate path | Yes\*    | -                |
| `MONGODB_TLS_CA_FILE`    | CA certificate path     | No       | -                |

\* Required for X.509 authentication

---

## 🧪 Testing

### Step 1: Validate Certificates

```bash
# Run certificate validation
uv run python mongodb_certificate_validator.py

# Or with specific paths
uv run python mongodb_certificate_validator.py \
  ~/mongodb_certs/mongodb-client.pem \
  ~/mongodb_certs/atlas-ca.pem
```

Expected output:

```
📋 Validating Client Certificate: /path/to/mongodb-client.pem
📜 CERTIFICATE INFORMATION:
   Subject: {'commonName': 'myuser', ...}
   Valid From: 2025-09-30 00:00:00
   Valid Until: 2026-09-30 00:00:00
   ...
✅ Certificate validation passed with no issues
```

### Step 2: Test MongoDB Connection

```bash
# Run comprehensive connection test
uv run python test_mongodb_connection.py
```

Expected output:

```
======================================================================
  STEP 1: Certificate Validation
======================================================================
✅ Certificate validation passed

======================================================================
  STEP 2: MongoDB Connection Test
======================================================================
🔌 Attempting to connect to MongoDB...
✅ MongoDB connection successful!

📊 Database Statistics:
   Database: visa_community
   Total Documents: 0
```

### Step 3: Manual Connection Test

```bash
# Test with Python directly
uv run python -c "
from mongodb_connection import mongodb_client
if mongodb_client.test_connection():
    print('✅ Connection successful!')
    print(mongodb_client.get_stats())
else:
    print('❌ Connection failed')
"
```

---

## 🔧 Troubleshooting

### Issue: "Certificate file not found"

**Solution:**

```bash
# Check if file exists
ls -la /path/to/mongodb-client.pem

# Verify permissions
chmod 600 /path/to/mongodb-client.pem

# Use absolute path in .env
MONGODB_TLS_CERT_FILE=/Users/neekrish/mongodb_certs/mongodb-client.pem
```

### Issue: "Authentication failed"

**Possible causes:**

1. **Certificate subject doesn't match Atlas user**

   ```bash
   # Check certificate subject
   openssl x509 -in mongodb-client.pem -noout -subject

   # Should match the user created in Atlas
   # Example: CN=myuser,OU=myorg,O=MyCompany
   ```

2. **Certificate expired**

   ```bash
   # Check expiration date
   openssl x509 -in mongodb-client.pem -noout -dates
   ```

3. **Wrong authentication mechanism**
   ```bash
   # Ensure .env has:
   MONGODB_AUTH_MECHANISM=MONGODB-X509
   ```

### Issue: "SSL certificate verify failed"

**Solution:**

```bash
# Download correct CA bundle
curl -o atlas-ca.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Update .env
MONGODB_TLS_CA_FILE=/path/to/atlas-ca.pem
```

### Issue: "Connection timeout"

**Possible causes:**

1. **IP not whitelisted in Atlas**

   - Go to: Network Access → Add IP Address
   - Add your current IP or `0.0.0.0/0` for dev

2. **Firewall blocking connection**

   ```bash
   # Test connectivity
   nc -zv cluster0.xxxxx.mongodb.net 27017
   ```

3. **Wrong connection string**
   ```bash
   # Verify connection string format
   # Should be: mongodb+srv://cluster.mongodb.net/
   # NOT: mongodb+srv://username:password@cluster.mongodb.net/
   ```

### Issue: "Certificate permissions warning"

**Solution:**

```bash
# Fix permissions (certificate should not be world-readable)
chmod 600 mongodb-client.pem
chmod 600 atlas-ca.pem

# Verify
ls -la mongodb-client.pem
# Should show: -rw-------
```

---

## 📚 Additional Resources

- [MongoDB X.509 Authentication Docs](https://www.mongodb.com/docs/manual/core/security-x.509/)
- [MongoDB Atlas Security](https://www.mongodb.com/docs/atlas/security/)
- [OpenSSL Documentation](https://www.openssl.org/docs/)

---

## 🔒 Security Best Practices

1. **Never commit certificates to version control**

   ```bash
   # Add to .gitignore
   echo "*.pem" >> .gitignore
   echo "mongodb_certs/" >> .gitignore
   ```

2. **Use strong private keys**

   - Minimum 2048-bit RSA keys
   - Consider 4096-bit for production

3. **Rotate certificates regularly**

   - Set expiration dates (e.g., 365 days)
   - Implement certificate rotation process

4. **Restrict certificate permissions**

   ```bash
   chmod 600 *.pem
   ```

5. **Use separate certificates for dev/staging/production**

6. **Monitor certificate expiration**
   - Set up alerts 30 days before expiration
   - Use the validation script regularly

---

## ✅ Quick Start Checklist

- [ ] MongoDB Atlas cluster created (M10+ tier)
- [ ] X.509 user created in Atlas with correct subject
- [ ] Client certificate generated
- [ ] CA certificate downloaded
- [ ] Certificates stored securely with proper permissions
- [ ] `.env` file configured with certificate paths
- [ ] Certificate validation passed
- [ ] Connection test successful
- [ ] Application started without errors

---

**Need help?** Check the logs for detailed error messages or run the test scripts above.
