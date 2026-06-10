import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from app.config import settings

logger = logging.getLogger("app.database")

class Database:
    client: AsyncIOMotorClient = None
    db = None
    fs = None
    
    # Collections
    return_requests = None
    return_items = None
    return_images_metadata = None
    audit_logs = None
    agent_conversations = None
    
    # Config/Workflow collections
    return_methods = None
    return_reasons = None
    settings_col = None
    shipping_labels = None

db = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URI)
        db.db = db.client[settings.MONGODB_DATABASE]
        
        # GridFS bucket initialization
        db.fs = AsyncIOMotorGridFSBucket(db.db)
        
        # Reference collections
        db.return_requests = db.db["return_requests"]
        db.return_items = db.db["return_items"]
        db.return_images_metadata = db.db["return_images_metadata"]
        db.audit_logs = db.db["audit_logs"]
        db.agent_conversations = db.db["agent_conversations"]
        
        db.return_methods = db.db["return_methods"]
        db.return_reasons = db.db["return_reasons"]
        db.settings_col = db.db["settings"]
        db.shipping_labels = db.db["shipping_labels"]
        
        # Connection validation ping
        await db.db.command("ping")
        logger.info(f"MongoDB connected successfully: {settings.MONGODB_DATABASE}")
        
        # Seed configurations
        await seed_database_configs()
    except Exception as e:
        logger.error(f"Failed to establish connection to MongoDB: {e}")
        db.db = None
        db.fs = None

async def seed_database_configs():
    logger.info("Checking database configuration seed status...")
    
    # 1. Seed Return Methods
    methods_count = await db.return_methods.count_documents({})
    if methods_count == 0:
        logger.info("Seeding default return methods...")
        await db.return_methods.insert_many([
            {"_id": "refund", "method": "refund", "active": True},
            {"_id": "credit", "method": "credit", "active": True},
            {"_id": "exchange", "method": "exchange", "active": True}
        ])

    # 2. Seed Return Reasons
    reasons_count = await db.return_reasons.count_documents({})
    if reasons_count == 0:
        logger.info("Seeding default return reasons...")
        await db.return_reasons.insert_many([
            {
                "_id": "damaged",
                "reason": "Damaged Product",
                "requires_image": True,
                "requires_notes": True,
                "requires_additional_reason": False
            },
            {
                "_id": "wrong_item",
                "reason": "Wrong Item",
                "requires_image": False,
                "requires_notes": True,
                "requires_additional_reason": False
            },
            {
                "_id": "size_mismatch",
                "reason": "Size Didn't Fit",
                "requires_image": False,
                "requires_notes": False,
                "requires_additional_reason": False
            },
            {
                "_id": "changed_mind",
                "reason": "Changed Mind",
                "requires_image": False,
                "requires_notes": False,
                "requires_additional_reason": False
            },
            {
                "_id": "defective",
                "reason": "Product Defective",
                "requires_image": True,
                "requires_notes": True,
                "requires_additional_reason": False
            },
            {
                "_id": "misplaced",
                "reason": "Order Misplaced",
                "requires_image": False,
                "requires_notes": True,
                "requires_additional_reason": True
            }
        ])

    # 3. Seed Global Settings
    settings_count = await db.settings_col.count_documents({})
    if settings_count == 0:
        logger.info("Seeding global workflow settings...")
        await db.settings_col.insert_one({
            "_id": "global_config",
            "restocking_fee_percentage": 0.10,        # 10% restocking fee
            "store_credit_bonus_percentage": 0.10,    # 10% bonus for choosing store credit
            "tax_percentage": 0.08                    # 8% standard tax
        })

async def close_mongo_connection():
    if db.client:
        db.client.close()
        logger.info("MongoDB client connection closed.")
