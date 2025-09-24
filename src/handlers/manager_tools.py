import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from firebase_admin import firestore

db = firestore.client()


async def _fetch_manager_properties(manager_id: str) -> List[Dict]:
    def _sync():
        props = db.collection("properties").document(manager_id).collection("listings").stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in props]
    return await asyncio.to_thread(_sync)


async def _fetch_bookings_for_property(manager_id: str, property_id: str) -> List[Dict]:
    def _sync():
        bookings = db.collection("properties").document(manager_id).collection("listings").document(property_id).collection("bookings").stream()
        results = []
        for doc in bookings:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        return results
    return await asyncio.to_thread(_sync)


async def bookings_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    manager_id = str(update.effective_user.id)
    today = datetime.now().date()

    properties = await _fetch_manager_properties(manager_id)
    results: List[str] = []
    for prop in properties:
        property_id = prop.get("id")
        property_name = prop.get("name", property_id)
        bookings = await _fetch_bookings_for_property(manager_id, property_id)
        for booking in bookings:
            check_in = booking.get("check_in")
            check_out = booking.get("check_out")
            payment_status = booking.get("payment_status", "Unknown")
            guest_name = booking.get("guest_name", "Guest")

            if hasattr(check_in, "date"):
                check_in_date = check_in.date()
            else:
                check_in_date = datetime.fromisoformat(check_in).date() if isinstance(check_in, str) else None

            if hasattr(check_out, "date"):
                check_out_date = check_out.date()
            else:
                check_out_date = datetime.fromisoformat(check_out).date() if isinstance(check_out, str) else None

            if check_in_date == today or check_out_date == today:
                fmt_in = check_in_date.strftime("%d %b") if check_in_date else "-"
                fmt_out = check_out_date.strftime("%d %b") if check_out_date else "-"
                results.append(
                    f"Guest: {guest_name}\nProperty: {property_name}\nCheck-in: {fmt_in}\nCheck-out: {fmt_out}\nPayment: {payment_status}"
                )

    if not results:
        await update.message.reply_text("No check-ins or check-outs today.")
    else:
        await update.message.reply_text("\n\n".join(results))


async def availability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    manager_id = str(update.effective_user.id)
    properties = await _fetch_manager_properties(manager_id)
    if not properties:
        await update.message.reply_text("No properties found for your account.")
        return

    keyboard = [[InlineKeyboardButton(p.get("name", p["id"]), callback_data=f"avail:{p['id']}")] for p in properties]
    await update.message.reply_text(
        "Select a property to view availability:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _availability_for_next_days(manager_id: str, property_id: str, days: int = 14) -> List[Tuple[datetime, bool]]:
    bookings = await _fetch_bookings_for_property(manager_id, property_id)
    today = datetime.now().date()
    window = [today + timedelta(days=i) for i in range(days)]

    booked_dates = set()
    for b in bookings:
        ci = b.get("check_in")
        co = b.get("check_out")

        if hasattr(ci, "date"):
            ci_d = ci.date()
        else:
            ci_d = datetime.fromisoformat(ci).date() if isinstance(ci, str) else None

        if hasattr(co, "date"):
            co_d = co.date()
        else:
            co_d = datetime.fromisoformat(co).date() if isinstance(co, str) else None

        if ci_d and co_d:
            current = ci_d
            while current <= co_d:
                booked_dates.add(current)
                current += timedelta(days=1)

    return [(d, d in booked_dates) for d in window]


async def on_availability_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # format avail:property_id
    _, property_id = data.split(":", 1)
    manager_id = str(update.effective_user.id)

    try:
        availability_list = await _availability_for_next_days(manager_id, property_id, 14)
        # Fetch property name
        def _sync_get_prop():
            doc = db.collection("properties").document(manager_id).collection("listings").document(property_id).get()
            return doc.to_dict() if doc.exists else None
        prop = await asyncio.to_thread(_sync_get_prop)
        prop_name = (prop or {}).get("name", property_id)

        lines = [f"{prop_name}:"]
        for d, booked in availability_list:
            lines.append(f"{d.strftime('%d %b')} - {'Booked' if booked else 'Available'}")
        await query.edit_message_text("\n".join(lines))
    except Exception:
        await query.edit_message_text("Could not load availability. Please try again later.")


async def price_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /price_recommendation <property_id>")
        return

    manager_id = str(update.effective_user.id)
    property_id = args[0]

    # Get bookings and property info
    bookings = await _fetch_bookings_for_property(manager_id, property_id)

    # Resolve property name and base price
    def _sync_prop():
        doc = db.collection("properties").document(manager_id).collection("listings").document(property_id).get()
        return doc.to_dict() if doc.exists else None
    prop = await asyncio.to_thread(_sync_prop)
    if not prop:
        await update.message.reply_text("Property not found.")
        return
    prop_name = prop.get("name", property_id)
    base_price = prop.get("price_per_night") or prop.get("base_price") or 45000

    # Compute occupancy next 14 days
    today = datetime.now().date()
    end = today + timedelta(days=14)
    total_days = 14

    booked_days = 0
    for b in bookings:
        ci = b.get("check_in")
        co = b.get("check_out")

        if hasattr(ci, "date"):
            ci_d = ci.date()
        else:
            ci_d = datetime.fromisoformat(ci).date() if isinstance(ci, str) else None

        if hasattr(co, "date"):
            co_d = co.date()
        else:
            co_d = datetime.fromisoformat(co).date() if isinstance(co, str) else None

        if not ci_d or not co_d:
            continue

        period_start = max(today, ci_d)
        period_end = min(end, co_d)
        current = period_start
        while current < period_end:
            booked_days += 1
            current += timedelta(days=1)

    occupancy = (booked_days / total_days) * 100
    if occupancy < 30:
        suggested = int(round(base_price * 0.85, -2))
        msg = f"Suggested price for {prop_name}: ₦{suggested:,}/night (based on current demand)."
    elif occupancy > 80:
        suggested = int(round(base_price * 1.20, -2))
        msg = f"Suggested price for {prop_name}: ₦{suggested:,}/night (based on current demand)."
    else:
        suggested = int(base_price)
        msg = f"Suggested price for {prop_name}: ₦{suggested:,}/night (based on current demand)."

    await update.message.reply_text(msg)


def get_availability_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(on_availability_select, pattern=r"^avail:.*$")


