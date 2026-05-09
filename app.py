from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta, timezone
import os
import requests
import jpholiday

from google.transit import gtfs_realtime_pb2

app = Flask(__name__)

JST = timezone(timedelta(hours=9))
ODPT_API_KEY = os.environ.get("ODPT_API_KEY")

ODPT_REALTIME_URL = "https://api.odpt.org/api/v4/gtfs/realtime/ToeiBus"

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
        "saturday": [
            "07:02", "07:20", "07:38", "07:56",
            "08:13", "08:30", "08:50",
            "09:12", "09:32", "09:52",
            "10:13", "10:35", "10:58",
            "11:23", "11:48",
            "12:14", "12:38",
            "13:01", "13:25", "13:50",
            "14:13", "14:37",
            "15:01", "15:24", "15:47",
            "16:07", "16:27", "16:46",
            "17:04", "17:22", "17:40", "17:58",
            "18:16", "18:42",
            "19:09", "19:34",
            "20:03", "20:31",
            "21:05", "21:34",
            "22:04",
        ],
        "holiday": [
            "07:14", "07:36", "07:58",
            "08:19", "08:41",
            "09:02", "09:24", "09:45",
            "10:07", "10:29", "10:47",
            "11:06", "11:24", "11:41", "11:59",
            "12:17", "12:34", "12:54",
            "13:13", "13:32", "13:51",
            "14:10", "14:28", "14:46",
            "15:04", "15:22", "15:42",
            "16:02", "16:22", "16:41",
            "17:01", "17:20", "17:41",
            "18:01", "18:21", "18:42",
            "19:07", "19:37",
            "20:07", "20:36",
            "21:05", "21:35",
            "22:04",
        ],
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
        "saturday": [
            "06:39", "06:59",
            "07:19", "07:37", "07:56",
            "08:17", "08:37", "08:57",
            "09:16", "09:36", "09:56",
            "10:15", "10:35", "10:55",
            "11:19", "11:42",
            "12:06", "12:31", "12:55",
            "13:19", "13:43",
            "14:07", "14:30", "14:56",
            "15:21", "15:46",
            "16:07", "16:26", "16:44",
            "17:03", "17:21", "17:40", "17:58",
            "18:16", "18:38",
            "19:05", "19:31", "19:57",
            "20:26", "20:56",
            "21:28",
            "22:04",
        ],
        "holiday": [
            "06:54",
            "07:14", "07:34", "07:54",
            "08:14", "08:34", "08:56",
            "09:17", "09:41",
            "10:05", "10:28", "10:51",
            "11:10", "11:28", "11:46",
            "12:03", "12:20", "12:37", "12:54",
            "13:12", "13:30", "13:48",
            "14:07", "14:26", "14:44",
            "15:02", "15:20", "15:40", "15:59",
            "16:19", "16:39", "16:58",
            "17:18", "17:36", "17:58",
            "18:18", "18:38", "18:58",
            "19:24", "19:54",
            "20:24", "20:54",
            "21:29",
            "22:04",
        ],
    },
}


def get_day_type():
    today = datetime.now(JST)

    if jpholiday.is_holiday(today.date()) or today.weekday() == 6:
        return "holiday"
    elif today.weekday() == 5:
        return "saturday"
    else:
        return "weekday"


def get_remaining_buses(direction_key):
    now = datetime.now(JST)
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


def fetch_toei_realtime():
    if not ODPT_API_KEY:
        return {
            "ok": False,
            "reason": "ODPT_API_KEY が未設定です",
            "vehicles": [],
        }

    try:
        res = requests.get(
            ODPT_REALTIME_URL,
            params={"acl:consumerKey": ODPT_API_KEY},
            timeout=10,
        )
        res.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(res.content)

        vehicles = []

        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue

            vehicle = entity.vehicle

            trip_id = vehicle.trip.trip_id if vehicle.trip.trip_id else ""
            route_id = vehicle.trip.route_id if vehicle.trip.route_id else ""
            vehicle_id = vehicle.vehicle.id if vehicle.vehicle.id else ""
            stop_id = vehicle.stop_id if vehicle.stop_id else ""

            lat = None
            lon = None

            if vehicle.HasField("position"):
                lat = vehicle.position.latitude
                lon = vehicle.position.longitude

            vehicles.append({
                "entity_id": entity.id,
                "trip_id": trip_id,
                "route_id": route_id,
                "vehicle_id": vehicle_id,
                "stop_id": stop_id,
                "latitude": lat,
                "longitude": lon,
            })

        return {
            "ok": True,
            "reason": "",
            "vehicles": vehicles,
        }

    except Exception as e:
        return {
            "ok": False,
            "reason": str(e),
            "vehicles": [],
        }


def is_kame21_vehicle(vehicle):
    text = " ".join([
        vehicle.get("trip_id", ""),
        vehicle.get("route_id", ""),
        vehicle.get("vehicle_id", ""),
        vehicle.get("entity_id", ""),
    ])

    keywords = [
        "亀21",
        "亀２１",
        "kame21",
        "Kame21",
        "KAME21",
        "K21",
    ]

    return any(k in text for k in keywords)


def get_realtime_info(direction_key):
    realtime = fetch_toei_realtime()

    if not realtime["ok"]:
        return {
            "ok": False,
            "status": "error",
            "message": realtime["reason"],
            "current_place": "取得できません",
            "stop_count": "--",
            "goenji": "--",
            "vehicle_id": "--",
            "raw_count": 0,
        }

    all_vehicles = realtime["vehicles"]

    kame21_vehicles = [
        v for v in all_vehicles
        if is_kame21_vehicle(v)
    ]

    # 最初は方向判定が不確実なので、亀21っぽい車両を優先。
    # 見つからなければ都バス車両の先頭を仮表示。
    if kame21_vehicles:
        target = kame21_vehicles[0]
    elif all_vehicles:
        target = all_vehicles[0]
    else:
        target = None

    if not target:
        return {
            "ok": True,
            "status": "no_vehicle",
            "message": "現在走行中の車両が見つかりませんでした",
            "current_place": "車両なし",
            "stop_count": "--",
            "goenji": "なし",
            "vehicle_id": "--",
            "raw_count": 0,
        }

    direction_label = BUS_TIMES.get(direction_key, {}).get("label", "")

    return {
        "ok": True,
        "status": "success",
        "message": "リアルタイム情報を取得しました",
        "direction": direction_label,
        "current_place": "位置情報取得済み",
        "stop_count": "確認中",
        "goenji": "確認中",
        "vehicle_id": target.get("vehicle_id") or target.get("entity_id") or "--",
        "route_id": target.get("route_id") or "--",
        "trip_id": target.get("trip_id") or "--",
        "stop_id": target.get("stop_id") or "--",
        "latitude": target.get("latitude"),
        "longitude": target.get("longitude"),
        "raw_count": len(all_vehicles),
        "kame21_count": len(kame21_vehicles),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buses/<direction>")
def buses(direction):
    if direction not in BUS_TIMES:
        return jsonify({"error": "invalid direction"}), 404

    return jsonify(get_remaining_buses(direction))


@app.route("/api/realtime/<direction>")
def realtime(direction):
    if direction not in BUS_TIMES:
        return jsonify({"error": "invalid direction"}), 404

    return jsonify(get_realtime_info(direction))


@app.route("/api/realtime-debug")
def realtime_debug():
    realtime = fetch_toei_realtime()

    vehicles = realtime.get("vehicles", [])

    sample = vehicles[:20]

    return jsonify({
        "ok": realtime["ok"],
        "reason": realtime["reason"],
        "count": len(vehicles),
        "sample": sample,
    })


if __name__ == "__main__":
    app.run(debug=True)