from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = ""  # Or use Atlas URL

client = AsyncIOMotorClient(MONGO_URL)
db = client.schedulai

chat_collection = db.get_collection("chats")
user_collection = db.get_collection("users")
