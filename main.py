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

rooms_collection    = db["rooms"]
days_collection     = db["days"]
bookings_collection = db["bookings"]


# ── Get user from cookie ──────────────────────────────────────────────────────
def get_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return auth.verify_id_token(token)
    except:
        return None


# ── Check if a time clashes with existing bookings on a day ──────────────────
def has_clash(day_id, time: str, exclude_booking_id=None):
    """Returns True if the given time clashes with any existing booking on that day."""
    query = {"day_id": day_id}
    for b in bookings_collection.find(query):
        if exclude_booking_id and b["_id"] == exclude_booking_id:
            continue
        if b["time"] == time:
            return True
    return False


# ── Login page ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ── Dashboard (with optional room + day filters) ─────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    filter_room: str = None,
    filter_day:  str = None,
    error:       str = None
):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    user_email = user.get("email")
    rooms      = list(rooms_collection.find())
    bookings   = []

    for b in bookings_collection.find({"user": user_email}):
        day = days_collection.find_one({"_id": b["day_id"]})
        if not day:
            continue
        room = rooms_collection.find_one({"_id": day["room_id"]})
        if not room:
            continue
        if filter_room and room["name"] != filter_room:
            continue
        if filter_day and day["date"] != filter_day:
            continue
        bookings.append({
            "room": room["name"],
            "date": day["date"],
            "time": b["time"],
            "_id":  str(b["_id"])
        })

    return templates.TemplateResponse("dashboard.html", {
        "request":     request,
        "user":        user,
        "rooms":       rooms,
        "bookings":    bookings,
        "error":       error,
        "filter_room": filter_room or "",
        "filter_day":  filter_day  or ""
    })


# ── Add Room ──────────────────────────────────────────────────────────────────
# BUG FIX 1: Check for duplicate room name before inserting
@app.post("/add-room")
async def add_room(request: Request, name: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    # Prevent duplicate room names (case-insensitive)
    existing = rooms_collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        return RedirectResponse("/dashboard?error=duplicate_room", status_code=303)

    rooms_collection.insert_one({
        "name":  name,
        "owner": user.get("email")
    })
    return RedirectResponse("/dashboard", status_code=303)


# ── Book Room ─────────────────────────────────────────────────────────────────
# BUG FIX 4: Check for clash before creating booking
@app.post("/book-room")
async def book_room(
    request: Request,
    room: str = Form(...),
    date: str = Form(...),
    time: str = Form(...)
):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    room_doc = rooms_collection.find_one({"name": room})
    if not room_doc:
        return RedirectResponse("/dashboard", status_code=303)

    day_doc = days_collection.find_one({"room_id": room_doc["_id"], "date": date})
    if day_doc:
        day_id = day_doc["_id"]
    else:
        day_id = days_collection.insert_one({
            "room_id": room_doc["_id"],
            "date":    date
        }).inserted_id

    # Clash check: is this time already booked for this room+day?
    if has_clash(day_id, time):
        return RedirectResponse("/dashboard?error=clash", status_code=303)

    bookings_collection.insert_one({
        "day_id": day_id,
        "time":   time,
        "user":   user.get("email")
    })
    return RedirectResponse("/dashboard", status_code=303)


# ── Delete Booking ────────────────────────────────────────────────────────────
# BUG FIX 2: Verify the booking belongs to the current user before deleting
@app.post("/delete-booking")
async def delete_booking(request: Request, booking_id: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
        if not booking:
            return RedirectResponse("/dashboard", status_code=303)
        # Only delete if this booking belongs to the current user
        if booking.get("user") != user.get("email"):
            return RedirectResponse("/dashboard?error=not_your_booking", status_code=303)
        bookings_collection.delete_one({"_id": ObjectId(booking_id)})
    except:
        pass
    return RedirectResponse("/dashboard", status_code=303)


# ── Delete Room ───────────────────────────────────────────────────────────────
@app.post("/delete-room")
async def delete_room(request: Request, room_id: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    try:
        room = rooms_collection.find_one({"_id": ObjectId(room_id)})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    if not room:
        return RedirectResponse("/dashboard", status_code=303)

    # Only the owner can delete
    if room.get("owner") != user.get("email"):
        return RedirectResponse("/dashboard?error=not_owner", status_code=303)

    # Block deletion if any bookings exist on this room's days
    for day in days_collection.find({"room_id": room["_id"]}):
        if bookings_collection.find_one({"day_id": day["_id"]}):
            return RedirectResponse("/dashboard?error=has_bookings", status_code=303)

    rooms_collection.delete_one({"_id": ObjectId(room_id)})
    return RedirectResponse("/dashboard", status_code=303)


# ── Edit Booking Page ─────────────────────────────────────────────────────────
# BUG FIX 3: Verify the booking belongs to the current user before showing edit page
@app.get("/edit/{booking_id}", response_class=HTMLResponse)
async def edit_page(request: Request, booking_id: str):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    if not booking:
        return RedirectResponse("/dashboard", status_code=303)

    # Only the owner of this booking can edit it
    if booking.get("user") != user.get("email"):
        return RedirectResponse("/dashboard?error=not_your_booking", status_code=303)

    return templates.TemplateResponse("edit.html", {
        "request":    request,
        "booking_id": booking_id,
        "time":       booking.get("time", "")
    })


# ── Update Booking ────────────────────────────────────────────────────────────
# BUG FIX 3+4: Verify ownership AND check for clash before updating
@app.post("/update-booking")
async def update_booking(
    request: Request,
    booking_id: str = Form(...),
    time:       str = Form(...)
):
    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    try:
        booking_oid = ObjectId(booking_id)
        booking     = bookings_collection.find_one({"_id": booking_oid})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    if not booking:
        return RedirectResponse("/dashboard", status_code=303)

    # Only the owner of this booking can update it
    if booking.get("user") != user.get("email"):
        return RedirectResponse("/dashboard?error=not_your_booking", status_code=303)

    # Clash check: exclude current booking from clash detection
    if has_clash(booking["day_id"], time, exclude_booking_id=booking_oid):
        return RedirectResponse(f"/edit/{booking_id}?error=clash", status_code=303)

    bookings_collection.update_one(
        {"_id": booking_oid},
        {"$set": {"time": time}}
    )
    return RedirectResponse("/dashboard", status_code=303)


# ── Room Detail Page ──────────────────────────────────────────────────────────
@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room_detail(request: Request, room_id: str):
    from datetime import datetime, timedelta

    user = get_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    try:
        room = rooms_collection.find_one({"_id": ObjectId(room_id)})
    except:
        return RedirectResponse("/dashboard", status_code=303)

    if not room:
        return RedirectResponse("/dashboard", status_code=303)

    # All bookings for this room grouped by date
    days = list(days_collection.find({"room_id": room["_id"]}))
    bookings_by_day = {}

    for day in days:
        day_bookings = list(bookings_collection.find({"day_id": day["_id"]}))
        if day_bookings:
            bookings_by_day[day["date"]] = [
                {
                    "time": b["time"],
                    "user": b["user"],
                    "_id":  str(b["_id"])
                }
                for b in sorted(day_bookings, key=lambda x: x["time"])
            ]

    sorted_days = sorted(bookings_by_day.items())

    # Occupancy for next 5 days (09:00-18:00 = 540 minutes)
    WORK_START = 9 * 60
    WORK_END   = 18 * 60
    WORK_MINS  = WORK_END - WORK_START

    today    = datetime.now().date()
    occupancy = []

    for i in range(5):
        target_date = today + timedelta(days=i)
        date_str    = target_date.strftime("%Y-%m-%d")
        bookings    = bookings_by_day.get(date_str, [])

        booked_starts = set()
        booked_mins   = 0
        for b in bookings:
            try:
                h, m          = map(int, b["time"].split(":"))
                start         = h * 60 + m
                end           = start + 60
                booked_starts.add(start)
                clamped_start = max(start, WORK_START)
                clamped_end   = min(end,   WORK_END)
                if clamped_end > clamped_start:
                    booked_mins += clamped_end - clamped_start
            except:
                pass

        pct = min(round((booked_mins / WORK_MINS) * 100), 100)

        earliest_free = None
        for slot in range(WORK_START, WORK_END - 60 + 1, 60):
            if slot not in booked_starts:
                h = slot // 60
                m = slot % 60
                earliest_free = f"{h:02d}:{m:02d}"
                break

        occupancy.append({
            "date":          date_str,
            "label":         target_date.strftime("%a %d %b"),
            "short":         target_date.strftime("%a"),
            "day_num":       target_date.strftime("%d"),
            "pct":           pct,
            "booked":        len(bookings),
            "earliest_free": earliest_free,
            "booked_slots":  list(booked_starts)
        })

    return templates.TemplateResponse("room_detail.html", {
        "request":     request,
        "user":        user,
        "room":        room,
        "sorted_days": sorted_days,
        "occupancy":   occupancy
    })