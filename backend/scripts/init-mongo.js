// Create admin user
db.createUser({
  user: "visa_admin",
  pwd: "visa_password",
  roles: [
    { role: "userAdminAnyDatabase", db: "admin" },
    { role: "readWriteAnyDatabase", db: "admin" }
  ]
});

// Switch to visa_community database
db = db.getSiblingDB('visa_community');

// Create collections
db.createCollection('users');
db.createCollection('chat_messages');
db.createCollection('sessions');

// Create indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.chat_messages.createIndex({ "timestamp": -1 });
db.sessions.createIndex({ "expires": 1 }, { expireAfterSeconds: 0 });


