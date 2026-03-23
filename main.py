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
client = MongoClient("mongodb+srv://chyash650:Yash50@cluster0.fyopc3i.mongodb.net/?retryWrites=true&w=majority")
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


# 🔹 HOME (Task 6 + 7)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = verify_token(request)

    rooms = list(rooms_collection.find())
    filter_room = request.query_params.get("filter_room")

    bookings = []

    if user:
        user_bookings = bookings_collection.find({"user": user["email"]})
    else:
        user_bookings = []

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


# 🔹 Add room (Task 3 + 12)
@app.post("/add-room")
async def add_room(request: Request, name: str = Form(...), capacity: int = Form(...)):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    rooms_collection.insert_one({
        "name": name,
        "capacity": capacity,
        "created_by": user["email"]
    })

    return RedirectResponse(url="/", status_code=303)


# 🔹 Delete room (Task 12)
@app.post("/delete-room")
async def delete_room(request: Request, room_id: str = Form(...)):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    room = rooms_collection.find_one({"_id": ObjectId(room_id)})

    if not room:
        return RedirectResponse(url="/", status_code=303)

    # Only creator can delete
    if room.get("created_by") != user["email"]:
        return RedirectResponse(url="/", status_code=303)

    # Check bookings exist
    days = days_collection.find({"room_id": room["_id"]})
    for d in days:
        if bookings_collection.find_one({"day_id": d["_id"]}):
            return RedirectResponse(url="/", status_code=303)

    days_collection.delete_many({"room_id": room["_id"]})
    rooms_collection.delete_one({"_id": room["_id"]})

    return RedirectResponse(url="/", status_code=303)


# 🔹 Book room (Task 5)
@app.post("/book-room")
async def book_room(request: Request, room: str = Form(...), date: str = Form(...), time: str = Form(...)):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

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

    existing = bookings_collection.find_one({
        "day_id": day_id,
        "time": time
    })

    if existing:
        return RedirectResponse(url="/", status_code=303)

    bookings_collection.insert_one({
        "day_id": day_id,
        "time": time,
        "user": user["email"]
    })

    return RedirectResponse(url="/", status_code=303)


# 🔹 Delete booking (Task 8 + 9)
@app.post("/delete-booking")
async def delete_booking(request: Request, booking_id: str = Form(...)):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    bookings_collection.delete_one({"_id": ObjectId(booking_id)})

    return RedirectResponse(url="/", status_code=303)


# 🔹 Edit page (Task 10 + 11)
@app.get("/edit-booking", response_class=HTMLResponse)
async def edit_booking_page(request: Request, booking_id: str):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
    day = days_collection.find_one({"_id": booking["day_id"]})
    room = rooms_collection.find_one({"_id": day["room_id"]})

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "booking_id": booking_id,
        "room": room["name"],
        "date": day["date"],
        "time": booking["time"]
    })


# 🔹 Update booking (Task 11)
@app.post("/update-booking")
async def update_booking(request: Request, booking_id: str = Form(...), date: str = Form(...), time: str = Form(...)):
    user = verify_token(request)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
    old_day = days_collection.find_one({"_id": booking["day_id"]})

    day_doc = days_collection.find_one({
        "room_id": old_day["room_id"],
        "date": date
    })

    if not day_doc:
        new_day_id = days_collection.insert_one({
            "room_id": old_day["room_id"],
            "date": date
        }).inserted_id
    else:
        new_day_id = day_doc["_id"]

    bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "day_id": new_day_id,
            "time": time
        }}
    )

    return RedirectResponse(url="/", status_code=303)