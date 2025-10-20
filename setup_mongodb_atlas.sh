#!/bin/bash

echo "🚀 Setting up MongoDB Atlas Configuration"
echo "========================================"

# Create .env file with MongoDB Atlas configuration
echo "📝 Creating .env file with MongoDB Atlas configuration..."
cat > .env << 'EOF'
# MongoDB Atlas Configuration with X.509 Certificate Authentication
MONGODB_URI=mongodb+srv://usvisacommunity.9mewkyh.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=usvisacommunity
MONGODB_DATABASE=visa_community
MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=/app/certificates/mongodb-cert.pem
MONGODB_AUTH_MECHANISM=MONGODB-X509

# Email Configuration (Mock mode for development)
EMAIL_MODE=mock

# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_HOST=http://host.docker.internal:11434

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Application Configuration
PYTHONUNBUFFERED=1
PYTHONPATH=/app/backend
EOF

echo "✅ .env file created"

# Check if certificates directory exists
if [ ! -d "certificates" ]; then
    echo "📁 Creating certificates directory..."
    mkdir -p certificates
fi

# Look for certificate files
echo "🔍 Looking for MongoDB certificate files..."
CERT_FILES=$(find certificates -name "*.pem" -o -name "*.crt" -o -name "*.p12" 2>/dev/null)

if [ -z "$CERT_FILES" ]; then
    echo "⚠️  No certificate files found in ./certificates/ directory"
    echo "   Please place your MongoDB X.509 certificate in the certificates/ directory"
    echo "   Supported formats: .pem, .crt, .p12"
    echo ""
    echo "📋 Next steps:"
    echo "1. Download your MongoDB X.509 certificate from MongoDB Atlas"
    echo "2. Place it in the ./certificates/ directory"
    echo "3. Rename it to 'mongodb-cert.pem' (or update the path in .env)"
    echo "4. Run this script again"
    exit 1
fi

# Get the first certificate file
CERT_FILE=$(echo "$CERT_FILES" | head -n1)
echo "✅ Found certificate: $CERT_FILE"

# If the certificate is not named mongodb-cert.pem, copy it
if [ "$CERT_FILE" != "certificates/mongodb-cert.pem" ]; then
    echo "📋 Copying certificate to mongodb-cert.pem..."
    cp "$CERT_FILE" certificates/mongodb-cert.pem
    echo "✅ Certificate copied to certificates/mongodb-cert.pem"
fi

# Set proper permissions
echo "🔐 Setting certificate permissions..."
chmod 600 certificates/mongodb-cert.pem
echo "✅ Certificate permissions set"

# Test the connection
echo "🧪 Testing MongoDB Atlas connection..."
python3 test_mongodb_atlas.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 MongoDB Atlas setup completed successfully!"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Start the application: docker compose --profile web up visa-web -d"
    echo "2. Access the app: http://localhost:8001"
    echo "3. Test authentication by signing up with your email"
    echo ""
    echo "📊 The application will now use MongoDB Atlas instead of local MongoDB"
else
    echo ""
    echo "❌ MongoDB Atlas connection test failed"
    echo "   Please check your certificate and network connection"
    exit 1
fi

