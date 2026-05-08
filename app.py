from flask import Flask, render_template, jsonify
from datetime import datetime
import jpholiday

app = Flask(__name__)

BUS_TIMES = {
    "kameido": {
        "label": "亀戸駅方面",
        "weekday": [
            "07:03", "07:16", "07:32", "07:45", "07:59",
            "08:13", "08:26", "08:39", "08:52",
            "09:05", "09:18", "09:34", "09:52",
            "10:10", "10:28", "10:48",
            "11:13", "11:37",
            "12:05", "12:33", "12:58",
            "13:22", "13:47",
            "14:13", "14:38",
            "15:03", "15:24", "15:42",
            "16:00", "16:17", "16:32", "16:47",
            "17:02", "17:18", "17:33", "17:48",
            "18:04", "18:20", "18:38", "18:57",
            "19:17", "19:39",
            "20:03", "20:27", "20:51",
            "21:15", "21:39",
            "22:04",
        ],
        "saturday": [],
        "holiday": [],
    },
    "toyocho": {
        "label": "東陽町方面",
        "weekday": [
            "06:40", "06:55",
            "07:08", "07:21", "07:33", "07:45", "07:57",
            "08:09", "08:20", "08:32", "08:44", "08:56",
            "09:09", "09:22", "09:39", "09:56",
            "10:15", "10:36",
            "11:05", "11:34",
            "12:01", "12:28", "12:55",
            "13:19", "13:42",
            "14:05", "14:30", "14:55",
            "15:20", "15:41",
            "16:00", "16:17", "16:34", "16:49",
            "17:04", "17:19", "17:35", "17:50",
            "18:05", "18:21", "18:37", "18:55",
            "19:14", "19:34", "19:57",
            "20:22", "20:48",
            "21:12", "21:38",
            "22:04",
        ],
        "saturday": [],
        "holiday": [],
    },
}


def get_day_type():
    today = datetime.now()

    if jpholiday.is_holiday(today.date()) or today.weekday() == 6:
        return "holiday"
    elif today.weekday() == 5:
        return "saturday"
    else:
        return "weekday"


def get_remaining_buses(direction_key):
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    day_type = get_day_type()
    direction = BUS_TIMES[direction_key]
    times = direction.get(day_type, [])

    remaining = []

    for t in times:
        h, m = map(int, t.split(":"))
        bus_minutes = h * 60 + m

        if bus_minutes >= now_minutes:
            remaining.append(t)

    return {
        "stop": "竪川大橋北詰",
        "direction": direction["label"],
        "day_type": day_type,
        "now": now.strftime("%H:%M"),
        "buses": remaining,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buses/<direction>")
def buses(direction):
    if direction not in BUS_TIMES:
        return jsonify({"error": "invalid direction"}), 404

    return jsonify(get_remaining_buses(direction))


if __name__ == "__main__":
    app.run(debug=True)