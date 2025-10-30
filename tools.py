import json
import random
from typing import Optional, List, Dict, Any
import os
import smtplib
import ssl
import qrcode
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

DB_PATH = "./restaurants/restaurants.json"

def _load_data() -> List[Dict[str, Any]]:
    """Helper function to load the restaurant data from our JSON file."""
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def _save_data(data: List[Dict[str, Any]]):
    """Helper function to save updated data back to the JSON file."""
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def _get_restaurant(restaurantId: Optional[int] = None, 
                      restaurantName: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds a single restaurant by its ID or Name."""
    all_restaurants = _load_data()
    
    if restaurantId:
        return next((r for r in all_restaurants if r["id"] == restaurantId), None)
    
    if restaurantName:
        return next((r for r in all_restaurants if r["name"].lower() == restaurantName.lower()), None)
    
    return None

def find_restaurants(locationArea: Optional[str] = None, 
                     cuisine: Optional[str] = None) -> List[Dict[str, Any]]:
    """Finds restaurants based on location area and/or cuisine."""
    print(f"DEBUG: Running 'find_restaurants' with location={locationArea}, cuisine={cuisine}")
    restaurants = _load_data()
    filtered_results = []

    for restaurant in restaurants:
        matches_location = True
        matches_cuisine = True
        
        if locationArea:
            matches_location = restaurant["location_area"].lower() == locationArea.lower()
            
        if cuisine:
            matches_cuisine = any(c.lower() == cuisine.lower() for c in restaurant["cuisine"])
            
        if matches_location or matches_cuisine:
            
            filtered_results.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "location_area": restaurant["location_area"],
                "cuisine": restaurant["cuisine"],
                "capacity": restaurant["capacity"]
            })
            
    return filtered_results

def _send_confirmation_email(booking_details: Dict[str, Any]):
    """Generates a QR code and emails it to the user."""
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_pass = os.getenv("SENDER_APP_PASSWORD")
    
    if not sender_email or not sender_pass:
        print("DEBUG: Email credentials not set in .env. Skipping email.")
        return

    receiver_email = booking_details.get("user_contact")
    if "@" not in receiver_email:
        print(f"DEBUG: User contact '{receiver_email}' is not an email. Skipping.")
        return

    booking_id = booking_details.get("booking_id")
    
    print(f"DEBUG: Sending QR code for booking {booking_id} to {receiver_email}...")

    msg = MIMEMultipart()
    msg['Subject'] = f"Your GoodFoods Reservation is Confirmed! (ID: {booking_id})"
    msg['From'] = sender_email
    msg['To'] = receiver_email


    qr_data = json.dumps(booking_details, indent=2)
    qr_img = qrcode.make(qr_data)
    

    img_bytes = io.BytesIO()
    qr_img.save(img_bytes, format='PNG')
    img_bytes.seek(0) 
    body = f"""
    <html>
    <body>
        <h2>Your Reservation is Confirmed!</h2>
        <p>Thank you for booking with GoodFoods, {booking_details.get('user_name')}.</p>
        <p><b>Restaurant:</b> {booking_details.get('restaurant_name')}</p>
        <p><b>Time:</b> {booking_details.get('time')}</p>
        <p><b>Party Size:</b> {booking_details.get('party_size')}</p>
        <p>Please show this QR code at the host stand when you arrive:</p>
        <img src="cid:qr_code">
        <br>
        <p>(Your booking ID is {booking_id})</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    
    image = MIMEImage(img_bytes.read(), name="booking_qr.png")
    image.add_header('Content-ID', '<qr_code>') # This links to the cid in the HTML
    msg.attach(image)


    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("DEBUG: Email sent successfully!")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")

def check_availability(partySize: int, 
                       time: str, 
                       restaurantId: Optional[int] = None, 
                       restaurantName: Optional[str] = None) -> Dict[str, Any]:
    """Checks if a restaurant has a table. Finds restaurant by ID or Name."""
    print(f"DEBUG: Running 'check_availability' for id={restaurantId} or name={restaurantName}")
    
    restaurant = _get_restaurant(restaurantId, restaurantName)
    if not restaurant:
        return {"status": "error", "message": f"Sorry, I couldn't find a restaurant with that ID or name."}

    current_occupancy = 0
    for booking in restaurant["bookings"]:
        if booking["time"].lower() == time.lower():
            current_occupancy += booking["party_size"]
            
    if restaurant["capacity"] >= (current_occupancy + partySize):
        return {"status": "available", "restaurant_name": restaurant["name"]}
    else:
        return {
            "status": "full",
            "message": f"Sorry, {restaurant['name']} is full at {time}."
        }

def book_table(partySize: int, 
               time: str, 
               userName: str, 
               userContact: str,
               restaurantId: Optional[int] = None, 
               restaurantName: Optional[str] = None) -> Dict[str, Any]:
    """Books a table and sends a confirmation email with QR code."""
    print(f"DEBUG: Running 'book_table' for {userName} at id={restaurantId} or name={restaurantName}")

    restaurant = _get_restaurant(restaurantId, restaurantName)
    if not restaurant:
        return {"status": "error", "message": f"Sorry, I couldn't find a restaurant with that ID or name to book."}

    availability = check_availability(partySize, time, restaurantId=restaurant["id"])
    if availability["status"] != "available":
        return {"status": "error", "message": f"Booking failed. {availability['message']}"}

    all_restaurants = _load_data()
    booking_id = f"GF{restaurant['id']}{random.randint(100, 999)}"

    # Create the booking object
    new_booking_receipt = {
        "status": "confirmed",
        "booking_id": booking_id,
        "restaurant_name": restaurant["name"],
        "user_name": userName,
        "user_contact": userContact,
        "party_size": partySize,
        "time": time
    }
    
    internal_booking_record = {
        "booking_id": booking_id,
        "user_name": userName,
        "user_contact": userContact,
        "party_size": partySize,
        "time": time
    }
    
    # Save to JSON database
    for r in all_restaurants:
        if r["id"] == restaurant["id"]:
            r["bookings"].append(internal_booking_record)
            break
    _save_data(all_restaurants)
    
    _send_confirmation_email(new_booking_receipt)

    return new_booking_receipt


def get_menu(restaurantId: Optional[int] = None, 
             restaurantName: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves the menu, sorted by price. Finds restaurant by ID or Name."""
    print(f"DEBUG: Running 'get_menu' for id={restaurantId} or name={restaurantName}")
    
    restaurant = _get_restaurant(restaurantId, restaurantName)
    if not restaurant:
        return [{"error": "Sorry, I couldn't find a restaurant with that ID or name."}]
        
    menu = restaurant.get("menu", [{"message": "This restaurant has no menu listed."}])
    
   
    if menu and "price" in menu[0]:
        try:
            menu.sort(key=lambda item: item.get("price", 0))
        except Exception as e:
            print(f"DEBUG: Could not sort menu. {e}")
           
    return menu

def find_item_in_menus(item_name: str, 
                         budget: Optional[float] = None) -> List[Dict[str, Any]]:
    """Finds a specific menu item across all restaurants in the JSON."""
    print(f"DEBUG: Running 'find_item_in_menus' for item={item_name}, budget={budget}")
    
    all_restaurants = _load_data()
    found_items = []

    for restaurant in all_restaurants:
        for item in restaurant.get("menu", []):
            # Check if item name matches
            if item_name.lower() in item.get("item", "").lower():
                # Check budget
                if budget:
                    if item.get("price", float('inf')) <= budget:
                        found_items.append({
                            "name": restaurant["name"],
                            "item_name": item["item"],
                            "price": item["price"]
                        })
                else:
                    found_items.append({
                        "name": restaurant["name"],
                        "item_name": item["item"],
                        "price": item["price"]
                    })

    # Sort the results by price
    found_items.sort(key=lambda x: x.get("price", 0))
    return found_items