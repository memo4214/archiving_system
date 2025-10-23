from bson.objectid import ObjectId

# Dataset for The Hunger Games
hunger_games_dataset = {
    "_id": ObjectId("68f238ee4bf88416046e55a9"),
    "title": "The Hunger Games",
    "author": "Suzanne Collins",
    "year": "2008",
    "category": "Fiction",
    "subcategory": "Dystopian / Adventure",
    "image": "cb0dc430c7494baf8d5b1648784eb135_the.jpg"
}

# Function to get The Hunger Games dataset
def get_hunger_games_dataset():
    return hunger_games_dataset