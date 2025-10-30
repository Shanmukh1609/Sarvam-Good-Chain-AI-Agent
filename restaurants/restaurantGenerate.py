import json
import random
from faker import Faker

# Initialize Faker to generate fake data
fake = Faker()

# --- Configuration ---
NUM_RESTAURANTS = 75
LOCATION_AREAS = ["downtown", "midtown", "uptown", "eastside", "westside", "riverwalk", "market district"]

# Master menu list, categorized by cuisine
# This provides the "various food items" and "price" you requested
MASTER_MENU = {
    "Italian": [
        {"item": "Margherita Pizza", "price": 14.99},
        {"item": "Spaghetti Carbonara", "price": 18.50},
        {"item": "Fettuccine Alfredo", "price": 17.00},
        {"item": "Chicken Parmesan", "price": 22.00},
        {"item": "Lasagna Bolognese", "price": 19.50},
        {"item": "Bruschetta", "price": 9.00},
    ],
    "Mexican": [
        {"item": "Carne Asada Tacos", "price": 15.00},
        {"item": "Chicken Enchiladas", "price": 17.50},
        {"item": "Guacamole & Chips", "price": 11.00},
        {"item": "Queso Fundido", "price": 13.00},
        {"item": "Burrito Bowl", "price": 16.50},
    ],
    "American": [
        {"item": "Classic Cheeseburger", "price": 16.00},
        {"item": "BBQ Ribs", "price": 24.50},
        {"item": "Caesar Salad", "price": 13.00},
        {"item": "Buffalo Wings", "price": 15.50},
        {"item": "Mac & Cheese", "price": 14.00},
    ],
    # --- UPDATED INDIAN MENU ---
    "Indian": [
        {"item": "Butter Chicken", "price": 19.00},
        {"item": "Paneer Tikka Masala", "price": 18.00},
        {"item": "Samosas (2 pcs)", "price": 7.50},
        {"item": "Garlic Naan", "price": 4.50},
        {"item": "Chicken Biryani", "price": 20.00},
        {"item": "Palak Paneer", "price": 17.50},
        {"item": "Chole Bhature", "price": 16.00},
        {"item": "Masala Dosa", "price": 14.00},
        {"item": "Pani Puri (8 pcs)", "price": 9.00},
        {"item": "Bhel Puri", "price": 8.50},
        {"item": "Pav Bhaji", "price": 12.00},
        {"item": "Vada Pav", "price": 6.50},
    ],
    "Japanese": [
        {"item": "Sushi Platter (12 pcs)", "price": 25.00},
        {"item": "Tonkotsu Ramen", "price": 17.00},
        {"item": "Chicken Teriyaki Don", "price": 18.50},
        {"item": "Edamame", "price": 6.00},
        {"item": "Gyoza (6 pcs)", "price": 9.50},
    ]
}

def generate_restaurants():
    """Generates a list of restaurant dictionaries."""
    restaurants = []
    main_cuisines = list(MASTER_MENU.keys())

    for i in range(1, NUM_RESTAURANTS + 1):
        # Pick a main cuisine and a location
        main_cuisine = random.choice(main_cuisines)
        location = random.choice(LOCATION_AREAS)
        
        # Generate a realistic menu by sampling from the master list
        menu_size = random.randint(4, len(MASTER_MENU[main_cuisine]))
        menu = random.sample(MASTER_MENU[main_cuisine], menu_size)
        
        restaurant = {
            "id": 100 + i,
            "name": f"GoodFoods - {location.title()}",
            "location_area": location,
            "cuisine": [main_cuisine], # Primary cuisine
            "capacity": random.choice([30, 40, 50, 60, 75, 90, 100]),
            "menu": menu,
            "bookings": [] # Start with no bookings
        }
        
        # Add a secondary cuisine sometimes
        if random.random() > 0.6: # 40% chance of a secondary cuisine
            secondary_cuisine = random.choice(main_cuisines)
            if secondary_cuisine != main_cuisine:
                restaurant["cuisine"].append(secondary_cuisine)

        restaurants.append(restaurant)
        
    return restaurants

def save_to_json(data, filename="restaurants.json"):
    """Saves the generated data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated {len(data)} restaurants and saved to {filename}")

# --- Main execution ---
if __name__ == "__main__":
    restaurant_data = generate_restaurants()
    save_to_json(restaurant_data)