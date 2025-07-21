from pymongo import MongoClient
from dotenv import load_dotenv
import os


load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI")) # your mongo connection string
db = client[""]  # ⬅️ You can name your DB anything
chat_collection = db[""]  # Collection to store chatbot messages
