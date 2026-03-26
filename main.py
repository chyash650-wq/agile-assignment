print("MAIN FILE LOADED")
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import firebase_admin
from firebase_admin import credentials, auth

from pymongo import MongoClient
from bson import ObjectId

# Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

app = FastAPI()

# Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# MongoDB
client = MongoClient("mongodb+srv://chyash650:Yash50@cluster0.fyopc3i.mongodb.net/?appName=Cluster0")
db = client["A1-3192183"]

rooms_collection = db["rooms"]
days_collection = db["days"]
bookings_collection = db["bookings"]

# 🔹 Get user
def get_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return auth.verify_id_token(token)
    except:
        return None


# 🔹 Login Page
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# 🔹 Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_user(request)

    if not user:
        return RedirectResponse("/", status_code=303)

    user_email = user.get("email")

    rooms = list(rooms_collection.find())
    bookings = []

    user_bookings = bookings_collection.find({"user": user_email})

    for b in user_bookings:
        day = days_collection.find_one({"_id": b["day_id"]})
        room = rooms_collection.find_one({"_id": day["room_id"]})

        bookings.append({
            "room": room["name"],
            "date": day["date"],
            "time": b["time"],
            "_id": str(b["_id"])
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "rooms": rooms,
        "bookings": bookings
    })


# 🔹 Add Room
@app.post("/add-room")
async def add_room(request: Request, name: str = Form(...), capacity: int = Form(...)):
    user = get_user(request)

    rooms_collection.insert_one({
        "name": name,
        "capacity": capacity,
        "owner": user.get("email")
    })

    return RedirectResponse("/dashboard", status_code=303)


# 🔹 Book Room
@app.post("/book-room")
async def book_room(request: Request, room: str = Form(...), date: str = Form(...), time: str = Form(...)):
    user = get_user(request)

    room_doc = rooms_collection.find_one({"name": room})

    day_doc = days_collection.find_one({
        "room_id": room_doc["_id"],
        "date": date
    })

    if not day_doc:
        day_id = days_collection.insert_one({
            "room_id": room_doc["_id"],
            "date": date
        }).inserted_id
    else:
        day_id = day_doc["_id"]

    bookings_collection.insert_one({
        "day_id": day_id,
        "time": time,
        "user": user.get("email")
    })

    return RedirectResponse("/dashboard", status_code=303)


# 🔹 Delete Booking
@app.post("/delete-booking")
async def delete_booking(booking_id: str = Form(...)):
    bookings_collection.delete_one({"_id": ObjectId(booking_id)})
    return RedirectResponse("/dashboard", status_code=303)


# 🔥 EDIT PAGE (FIXED)
@app.get("/edit/{booking_id}", response_class=HTMLResponse)
async def edit_page(request: Request, booking_id: str):
    booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})

    if not booking:
        return HTMLResponse("Booking not found")

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "booking_id": booking_id,
        "time": booking.get("time")
    })


# 🔥 UPDATE BOOKING
@app.post("/update-booking")
async def update_booking(booking_id: str = Form(...), time: str = Form(...)):
    bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"time": time}}
    )

    return RedirectResponse("/dashboard", status_code=303)