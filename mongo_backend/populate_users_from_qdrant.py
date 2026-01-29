"""
Script to populate MongoDB users from Qdrant user profiles
Extracts demographics and generates credentials for MongoDB storage
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from passlib.context import CryptContext
from db_connection import MongoDBConnection
from config import COLLECTIONS
from bson import ObjectId
import uuid


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Qdrant connection
QDRANT_HOST = "192.168.1.128"
QDRANT_PORT = 6333
USERS_COLLECTION = "user_profiles"  # Default Qdrant collection name


def get_qdrant_client() -> QdrantClient:
    """Initialize Qdrant client."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def extract_user_data(qdrant_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant user data from Qdrant payload.
    
    Qdrant structure:
    {
        "user_id": "user_walid_eng",
        "demographics": {
            "age": "32",
            "gender": "M",
            "region": "Ariana",
            "status": "working",
            "device": "Linux Desktop"
        },
        ...
    }
    
    Returns MongoDB-ready user data (without credentials)
    """
    demographics = qdrant_payload.get("demographics", {})
    
    # Extract and normalize data
    user_id = qdrant_payload.get("user_id", "")
    age = demographics.get("age", "")
    gender = demographics.get("gender", "").upper()
    region = demographics.get("region", "")
    status = demographics.get("status", "")
    device = demographics.get("device", "")
    
    # Convert age to int if possible
    try:
        age_int = int(age) if age else None
    except (ValueError, TypeError):
        age_int = None
    
    # Normalize gender to M/F
    sex = "M" if gender == "M" else "F" if gender == "F" else None
    
    return {
        "user_id": user_id,
        "age": age_int,
        "sex": sex,
        "region": region,
        "status": status,
        "device": device
    }


def generate_email(user_id: str) -> str:
    """Generate email in format user1@gmail.com, user2@gmail.com, etc."""
    return f"{user_id}@gmail.com"


def create_mongo_user(user_data: Dict[str, Any], email: str, password: str = "123456") -> Dict[str, Any]:
    """
    Create complete MongoDB user document with credentials.
    
    Args:
        user_data: Extracted user data from Qdrant
        email: Generated email
        password: Plain text password (will be hashed)
    
    Returns:
        Complete MongoDB user document
    """
    user_id = user_data.get("user_id", "")
    
    # Hash password
    password_hash = pwd_context.hash(password)
    
    # Create MongoDB document
    now = datetime.utcnow().isoformat()
    
    return {
        "_id": user_id,  # Use Qdrant user_id as MongoDB _id
        "username": user_id,
        "email": email,
        "password_hash": password_hash,
        "first_name": "",  # Not available from Qdrant
        "last_name": "",   # Not available from Qdrant
        "age": user_data.get("age"),
        "sex": user_data.get("sex"),
        "status": user_data.get("status"),
        "region": user_data.get("region"),
        "device": user_data.get("device"),
        "address": {
            "street": "",
            "city": user_data.get("region", ""),  # Use region as city
            "state": "",
            "postal_code": "",
            "country": "Tunisia",  # Assuming Tunisia based on regions
        },
        "phone": "",
        "created_at": now,
        "updated_at": now,
    }


async def fetch_users_from_qdrant(collection_name: str = USERS_COLLECTION, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all users from Qdrant collection.
    
    Args:
        collection_name: Name of the Qdrant collection
        limit: Maximum number of users to fetch (None for all)
    
    Returns:
        List of user payloads
    """
    client = get_qdrant_client()
    
    users = []
    offset = None
    batch_size = 100
    
    print(f"Fetching users from Qdrant collection: {collection_name}")
    
    while True:
        # Scroll through all points
        result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points, next_offset = result
        
        if not points:
            break
        
        # Extract payloads
        for point in points:
            users.append(point.payload)
        
        print(f"Fetched {len(users)} users so far...")
        
        # Check if we've reached the limit
        if limit and len(users) >= limit:
            users = users[:limit]
            break
        
        # Check if there are more points
        if next_offset is None:
            break
        
        offset = next_offset
    
    print(f"Total users fetched: {len(users)}")
    return users


async def populate_users(qdrant_collection: str = USERS_COLLECTION, limit: Optional[int] = None, dry_run: bool = False):
    """
    Main function to populate MongoDB with users from Qdrant.
    
    Args:
        qdrant_collection: Name of Qdrant collection containing users
        limit: Maximum number of users to import (None for all)
        dry_run: If True, only show what would be imported without inserting
    """
    # Fetch users from Qdrant
    qdrant_users = await fetch_users_from_qdrant(qdrant_collection, limit)
    
    if not qdrant_users:
        print("No users found in Qdrant")
        return
    
    # Process each user
    mongo_users = []
    skipped_users = []
    
    for qdrant_user in qdrant_users:
        try:
            # Extract user data
            user_data = extract_user_data(qdrant_user)
            
            # Skip if no user_id
            if not user_data.get("user_id"):
                skipped_users.append("No user_id")
                continue
            
            # Generate email
            email = generate_email(user_data.get("user_id"))
            
            # Create MongoDB document
            mongo_user = create_mongo_user(user_data, email)
            mongo_users.append(mongo_user)
            
        except Exception as e:
            skipped_users.append(f"Error: {str(e)}")
            continue
    
    print(f"\n{'='*60}")
    print(f"Processed {len(qdrant_users)} users from Qdrant")
    print(f"Ready to import: {len(mongo_users)} users")
    print(f"Skipped: {len(skipped_users)} users")
    print(f"{'='*60}\n")
    
    if skipped_users:
        print("Skipped users:")
        for reason in skipped_users[:10]:  # Show first 10
            print(f"  - {reason}")
        if len(skipped_users) > 10:
            print(f"  ... and {len(skipped_users) - 10} more")
        print()
    
    if dry_run:
        print("DRY RUN - Not inserting to MongoDB")
        print("\nSample users (first 3):")
        for i, user in enumerate(mongo_users[:3], 1):
            print(f"\n{i}. User: {user['username']}")
            print(f"   Email: {user['email']}")
            print(f"   Age: {user.get('age')}, Sex: {user.get('sex')}, Status: {user.get('status')}")
            print(f"   Region: {user.get('region')}, Device: {user.get('device')}")
        return
    
    # Insert into MongoDB
    if not mongo_users:
        print("No users to insert")
        return
    
    print("Inserting users into MongoDB...")
    mongo = MongoDBConnection()
    mongo.connect()
    collection = mongo.get_collection(COLLECTIONS["users"])
    
    inserted_count = 0
    duplicate_count = 0
    error_count = 0
    
    for user in mongo_users:
        try:
            # Check if user already exists
            existing = collection.find_one({"_id": user["_id"]})
            if existing:
                duplicate_count += 1
                print(f"  ⚠️  User {user['username']} already exists, skipping")
                continue
            
            # Check if email already exists
            existing_email = collection.find_one({"email": user["email"]})
            if existing_email:
                # Generate new email if conflict
                email_counter += 1
                user["email"] = generate_email(email_counter)
                print(f" Email conflict, using {user['email']}")
            
            # Insert user
            collection.insert_one(user)
            inserted_count += 1
            print(f"  ✓ Inserted: {user['username']} ({user['email']})")
            
        except Exception as e:
            error_count += 1
            print(f"  ✗ Error inserting {user.get('username', 'unknown')}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Import complete!")
    print(f" Inserted: {inserted_count} users")
    print(f" Duplicates: {duplicate_count} users")
    print(f" Errors: {error_count} users")
    print(f"{'='*60}\n")
    print("All users have password: 123456")


async def main():
    """Interactive CLI for populating users."""
    print("=" * 60)
    print("MongoDB User Population from Qdrant")
    print("=" * 60)
    print()
    
    # Get Qdrant collection name
    collection_name = input(f"Enter Qdrant collection name [{USERS_COLLECTION}]: ").strip()
    if not collection_name:
        collection_name = USERS_COLLECTION
    
    # Get limit
    limit_input = input("Enter max users to import (press Enter for all): ").strip()
    limit = int(limit_input) if limit_input else None
    
    # Dry run option
    dry_run_input = input("Dry run? (y/n) [n]: ").strip().lower()
    dry_run = dry_run_input == 'y'
    
    print()
    
    # Confirm
    if not dry_run:
        confirm = input(f"Import users from '{collection_name}' to MongoDB? (y/n) [y]: ").strip().lower()
        if confirm == 'n':
            print("Cancelled")
            return
    
    # Run population
    await populate_users(collection_name, limit, dry_run)


if __name__ == "__main__":
    asyncio.run(main())
