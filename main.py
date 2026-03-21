from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import firebase_admin
from firebase_admin import credentials, auth

from pymongo import MongoClient
from bson import ObjectId

# 🔹 Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

app = FastAPI()

# 🔹 Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 🔹 MongoDB
client = MongoClient("mongodb+srv://chyash650:Yash50@cluster0.fyopc3i.mongodb.net/?appName=Cluster0")
db = client["A1-3192183"]

rooms_collection = db["rooms"]
days_collection = db["days"]
bookings_collection = db["bookings"]

# 🔹 Verify token
def verify_token(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return auth.verify_id_token(token)
    except:
        return None


# 🔹 HOME (Task 6 + Task 7)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = verify_token(request)

    rooms = list(rooms_collection.find())

    # 🔥 GET FILTER VALUE
    filter_room = request.query_params.get("filter_room")

    bookings = []

    if user:
        user_bookings = bookings_collection.find({"user": user["email"]})
    else:
        user_bookings = []

    for b in user_bookings:

        if "day_id" not in b:
            continue

        day = days_collection.find_one({"_id": b["day_id"]})
        if not day:
            continue

        room = rooms_collection.find_one({"_id": day["room_id"]})
        if not room:
            continue

        # 🔥 TASK 7 FILTER
        if filter_room and room["name"] != filter_room:
            continue

        bookings.append({
            "room": room["name"],
            "date": day["date"],
            "time": b["time"],
            "user": b["user"],
            "_id": str(b["_id"])
        })

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user": user,
        "rooms": rooms,
        "bookings": bookings,
        "filter_room": filter_room
    })


# 🔹 Add room
@app.post("/add-room")
async def add_room(name: str = Form(...), capacity: int = Form(...)):
    rooms_collection.insert_one({
        "name": name,
        "capacity": capacity
    })
    return RedirectResponse(url="/", status_code=303)


# 🔹 Book room
@app.post("/book-room")
async def book_room(
    request: Request,
    room: str = Form(...),
    date: str = Form(...),
    time: str = Form(...)
):
    user = verify_token(request)

    if not user:
        return {"error": "Not logged in"}

    if not room or not date or not time:
        return {"error": "Missing fields"}

    room_doc = rooms_collection.find_one({"name": room})
    if not room_doc:
        return {"error": "Room not found"}

    # 🔹 Find or create day
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

    # 🔴 Prevent double booking
    existing = bookings_collection.find_one({
        "day_id": day_id,
        "time": time
    })

    if existing:
        return {"error": "Room already booked!"}

    bookings_collection.insert_one({
        "day_id": day_id,
        "time": time,
        "user": user["email"]
    })

    return RedirectResponse(url="/", status_code=303)


# 🔥 DELETE BOOKING (Task 8)
@app.post("/delete-booking")
async def delete_booking(booking_id: str = Form(...)):
    bookings_collection.delete_one({"_id": ObjectId(booking_id)})
    return RedirectResponse(url="/", status_code=303)