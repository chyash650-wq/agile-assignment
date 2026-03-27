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


# 🔹 Login page
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# 🔹 Dashboard (with filter)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, filter_room: str = None):
    user = get_user(request)

    if not user:
        return RedirectResponse("/", status_code=303)

    user_email = user.get("email")

    rooms = list(rooms_collection.find())
    bookings = []

    user_bookings = bookings_collection.find({"user": user_email})

    for b in user_bookings:
        day = days_collection.find_one({"_id": b["day_id"]})
        if not day:
            continue

        room = rooms_collection.find_one({"_id": day["room_id"]})
        if not room:
            continue

        # 🔥 Filter (Task 7)
        if filter_room and room["name"] != filter_room:
            continue

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

    if not user:
        return RedirectResponse("/", status_code=303)

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

    if not user:
        return RedirectResponse("/", status_code=303)

    room_doc = rooms_collection.find_one({"name": room})
    if not room_doc:
        return RedirectResponse("/dashboard", status_code=303)

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
    try:
        bookings_collection.delete_one({"_id": ObjectId(booking_id)})
    except:
        pass
    return RedirectResponse("/dashboard", status_code=303)


# 🔥 DELETE ROOM (FULL SAFE VERSION)
@app.post("/delete-room")
async def delete_room(request: Request, room_id: str = Form(...)):
    user = get_user(request)

    if not user:
        return RedirectResponse("/", status_code=303)

    try:
        room = rooms_collection.find_one({"_id": ObjectId(room_id)})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    # ❌ Room not found
    if not room:
        return RedirectResponse("/dashboard", status_code=303)

    # ❌ Only owner
    if room.get("owner") != user.get("email"):
        return RedirectResponse("/dashboard", status_code=303)

    # ❌ Check bookings exist
    days = days_collection.find({"room_id": room["_id"]})

    for d in days:
        if bookings_collection.find_one({"day_id": d["_id"]}):
            return RedirectResponse("/dashboard", status_code=303)

    # ✅ Delete room
    rooms_collection.delete_one({"_id": ObjectId(room_id)})

    return RedirectResponse("/dashboard", status_code=303)


# 🔹 Edit Page
@app.get("/edit/{booking_id}", response_class=HTMLResponse)
async def edit_page(request: Request, booking_id: str):
    try:
        booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    if not booking:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "booking_id": booking_id,
        "time": booking.get("time", "")
    })


# 🔹 Update Booking
@app.post("/update-booking")
async def update_booking(booking_id: str = Form(...), time: str = Form(...)):
    try:
        bookings_collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"time": time}}
        )
    except:
        pass

    return RedirectResponse("/dashboard", status_code=303)