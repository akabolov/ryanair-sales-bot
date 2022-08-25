import consts as keys
from ryanair import Ryanair
from telegram.ext import *
import telegram
from dateutil.relativedelta import *
import airportsdata
import datetime
import math
import pytz

ryanair = Ryanair("USD")

users = {}
airports = airportsdata.load("IATA")
airports_codes = list(airports.keys())


def start_command(update, context):
    user_id = context._user_id_and_data[0]
    update.message.reply_text("Type Airport code (KRK, etc.)")
    users[user_id] = {"airport_codes": [], "destinations": [], "should_update": True}


def handle_add_airport_origin(update, context):
    airport_code = update.message.text.upper()
    if airport_code in airports.keys():
        user_id = context._user_id_and_data[0]
        if user_id not in users.keys():
            update.message.reply_text("Please run start command first.")
        elif airports[airport_code]:
            users[user_id]["airport_codes"].append(airport_code)
            update.message.reply_text("New airport successfully added.")
            send_update_for_user_id(context, user_id)
        else:
            update.message.reply_text("Airport does not exist")
            update.message.reply_text(
                "You can check airport IATA codes here: https://www.nationsonline.org/oneworld/IATA_Codes/airport_code_list.htm"
            )
    else:
        update.message.reply_text("Please provide correct airport code.")
        update.message.reply_text(
            "You can check airports here: https://www.nationsonline.org/oneworld/IATA_Codes/airport_code_list.htm"
        )


def error(update, context):
    print(f"Update {update} caused error {error}")


def pause_updates(update, context):
    user_id = context._user_id_and_data[0]
    if users[user_id]:
        users[user_id]["should_update"] = False
        update.message.reply_text("You will no longer receive updates.")


def start_updates(update, context):
    user_id = context._user_id_and_data[0]
    if users[user_id]:
        users[user_id]["should_update"] = True
        update.message.reply_text("From now on you will get ticket updates.")


def get_subscriptions(update, context):
    user_id = context._user_id_and_data[0]
    if user_id in users.keys():
        update.message.reply_text(" ".join(users[user_id]["airport_codes"]))
    else:
        update.message.reply_text("You have no subscriptions.")


def format_flight(flight):
    price = flight.price
    origin = flight.originFull
    destination = flight.destinationFull
    when = flight.departureTime.strftime("%Y-%m-%d, %H:%M")
    return f"<b>Price:</b> {price} \n<b>From:</b> {origin} \n<b>Destination:</b> {destination} \n<b>When:</b> {when}"


def get_chunks(lst, n):
    n = max(1, n)
    return (lst[i : i + n] for i in range(0, len(lst), n))


def send_update_message(context: CallbackContext, code: str, user_id: int):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    later = (datetime.datetime.now() + relativedelta(months=+6)).strftime("%Y-%m-%d")
    flights = ryanair.get_flights(code, now, later)
    test = list(map(format_flight, flights))
    message_length = len(" ".join(test))
    chunks_n = math.ceil(message_length / telegram.constants.MAX_MESSAGE_LENGTH)
    if chunks_n > 0:
        splitted_messages = list(get_chunks(test, math.ceil(len(test) / chunks_n)))

        for message in splitted_messages:
            result = "\n\n".join(message)
            context.bot.send_message(
                chat_id=str(user_id), text=result, parse_mode=telegram.ParseMode.HTML
            )


def send_update_for_user_id(context: CallbackContext, user_id: int):
    for code in users[user_id]["airport_codes"]:
        send_update_message(context, code, user_id)


def send_update(context: CallbackContext):
    for user_id in users:
        if users[user_id]["airport_codes"] and users[user_id]["should_update"]:
            for code in users[user_id]["airport_codes"]:
                send_update_message(context, code, user_id)


def main():
    updater = Updater(keys.API_KEY, use_context=True)
    jq = updater.job_queue
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("get_subscriptions", get_subscriptions))
    dp.add_handler(CommandHandler("pause_updates", pause_updates))
    dp.add_handler(CommandHandler("start_updates", start_updates))
    dp.add_handler(MessageHandler(Filters.text, handle_add_airport_origin))

    dp.add_error_handler(error)

    # update_queue = jq.run_repeating(send_update, interval=43200, first=10)
    update_queue = jq.run_daily(
        send_update,
        datetime.time(hour=12, minute=00, tzinfo=pytz.timezone("Europe/Vienna")),
        days=(0, 1, 2, 3, 4, 5, 6),
    )

    updater.start_polling()
    updater.idle()


main()
