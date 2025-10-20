#!/usr/bin/env python3
"""
Test MongoDB Atlas connection with X.509 certificate authentication
"""

from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
import sys
from pathlib import Path

def test_mongodb_atlas_connection():
    """Test MongoDB Atlas connection with X.509 certificate"""
    
    # Your MongoDB Atlas connection details
    uri = "mongodb+srv://usvisacommunity.9mewkyh.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority&appName=usvisacommunity"
    
    # Look for certificate files in the certificates directory
    cert_dir = Path(__file__).parent / "certificates"
    cert_files = list(cert_dir.glob("*.pem")) + list(cert_dir.glob("*.crt")) + list(cert_dir.glob("*.p12"))
    
    if not cert_files:
        print("❌ No certificate files found in ./certificates/ directory")
        print("   Please place your MongoDB X.509 certificate in the certificates/ directory")
        print("   Supported formats: .pem, .crt, .p12")
        return False
    
    cert_file = cert_files[0]
    print(f"🔍 Found certificate: {cert_file}")
    
    try:
        print("🔌 Connecting to MongoDB Atlas...")
        client = MongoClient(
            uri,
            tls=True,
            tlsCertificateKeyFile=str(cert_file),
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            server_api=ServerApi('1')
        )
        
        # Test connection
        print("📡 Testing connection...")
        client.admin.command('ping')
        print("✅ MongoDB Atlas connection successful!")
        
        # Test database access
        db = client['visa_community']
        print(f"📊 Database 'visa_community' accessible")
        
        # List collections
        collections = db.list_collection_names()
        print(f"📋 Collections: {collections}")
        
        # Test creating a test collection
        test_collection = db['test_connection']
        test_doc = {"test": "MongoDB Atlas connection", "timestamp": "2025-01-12"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ Write operation successful: {result.inserted_id}")
        
        # Test reading
        found_doc = test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Read operation successful: {found_doc}")
        
        # Clean up test collection
        test_collection.drop()
        print("🧹 Test collection cleaned up")
        
        # Test authentication collections
        print("\n🔐 Testing authentication collections...")
        
        # Test users collection
        users = db['users']
        user_count = users.count_documents({})
        print(f"👥 Users collection: {user_count} documents")
        
        # Test verification_codes collection
        codes = db['verification_codes']
        codes_count = codes.count_documents({})
        print(f"🔑 Verification codes collection: {codes_count} documents")
        
        # Test sessions collection
        sessions = db['sessions']
        sessions_count = sessions.count_documents({})
        print(f"🎫 Sessions collection: {sessions_count} documents")
        
        print("\n🎉 MongoDB Atlas connection test completed successfully!")
        print("✅ Your application should now work with MongoDB Atlas")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB Atlas connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if your certificate file is valid")
        print("2. Verify your MongoDB Atlas cluster is running")
        print("3. Ensure your IP is whitelisted in MongoDB Atlas")
        print("4. Check if the certificate has proper permissions")
        return False

if __name__ == "__main__":
    print("🚀 Testing MongoDB Atlas Connection")
    print("=" * 50)
    
    success = test_mongodb_atlas_connection()
    
    if success:
        print("\n✅ All tests passed! Your MongoDB Atlas setup is ready.")
        sys.exit(0)
    else:
        print("\n❌ Connection test failed. Please check your configuration.")
        sys.exit(1)
