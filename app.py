from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta, timezone
import os
import math
import csv
import requests
import jpholiday
from google.transit import gtfs_realtime_pb2

app = Flask(__name__)

JST = timezone(timedelta(hours=9))

ODPT_API_KEY = os.environ.get("ODPT_API_KEY")
ODPT_REALTIME_URL = "https://api.odpt.org/api/v4/gtfs/realtime/ToeiBus"

TARGET_ROUTE_ID = "058"

TARGET_LAT = 35.6960
TARGET_LON = 139.8225
SEARCH_RADIUS_KM = 5.0

STOPS_FILE = os.path.join("gtfs", "stops.txt")


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


def load_stop_names():
    stop_names = {}

    if not os.path.exists(STOPS_FILE):
        return stop_names

    try:
        with open(STOPS_FILE, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                stop_id = row.get("stop_id", "")
                stop_name = row.get("stop_name", "")

                if stop_id and stop_name:
                    stop_names[stop_id] = stop_name

        return stop_names

    except Exception:
        return stop_names


STOP_NAMES = load_stop_names()


def get_stop_name(stop_id):
    if not stop_id:
        return "接近中"

    if stop_id in STOP_NAMES:
        return STOP_NAMES[stop_id]

    base_stop_id = stop_id.split("-")[0]

    if base_stop_id in STOP_NAMES:
        return STOP_NAMES[base_stop_id]

    return "接近中"


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


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


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

            item = {
                "entity_id": entity.id,
                "trip_id": trip_id,
                "route_id": route_id,
                "vehicle_id": vehicle_id,
                "stop_id": stop_id,
                "stop_name": get_stop_name(stop_id),
                "latitude": lat,
                "longitude": lon,
            }

            if lat is not None and lon is not None:
                item["distance_km"] = round(
                    distance_km(TARGET_LAT, TARGET_LON, lat, lon),
                    3,
                )
            else:
                item["distance_km"] = None

            vehicles.append(item)

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


def is_target_direction(vehicle, direction_key):
    trip_id = vehicle.get("trip_id", "")

    if direction_key == "kameido":
        return "-1-" in trip_id

    if direction_key == "toyocho":
        return "-2-" in trip_id

    return True


def get_target_vehicles(direction_key):
    realtime = fetch_toei_realtime()

    if not realtime["ok"]:
        return realtime

    vehicles = realtime["vehicles"]
    target = []

    for v in vehicles:
        if v.get("route_id") != TARGET_ROUTE_ID:
            continue

        if not is_target_direction(v, direction_key):
            continue

        if v.get("distance_km") is not None and v["distance_km"] <= SEARCH_RADIUS_KM:
            target.append(v)

    target.sort(
        key=lambda x: x["distance_km"] if x.get("distance_km") is not None else 9999
    )

    return {
        "ok": True,
        "reason": "",
        "vehicles": target,
        "all_count": len(vehicles),
    }


def get_stop_count_text(distance):
    if distance is None:
        return "確認中"

    if distance <= 0.25:
        return "まもなく"
    elif distance <= 0.7:
        return "あと1〜2停留所"
    elif distance <= 1.5:
        return "あと2〜4停留所"
    elif distance <= 3.0:
        return "あと4停留所以上"
    else:
        return "確認中"


def get_goenji_text(distance):
    if distance is None:
        return "確認中"

    if distance <= 0.25:
        return "なし"
    elif distance <= 1.0:
        return "少し豪炎寺"
    elif distance <= 3.0:
        return "豪炎寺中"
    else:
        return "確認中"


def get_realtime_info(direction_key):
    result = get_target_vehicles(direction_key)

    if not result["ok"]:
        return {
            "ok": False,
            "status": "error",
            "message": result["reason"],
            "current_place": "取得できません",
            "stop_name": "取得できません",
            "stop_count": "--",
            "goenji": "--",
            "vehicle_id": "--",
            "route_id": "--",
            "trip_id": "--",
            "stop_id": "--",
            "distance_km": None,
            "target_count": 0,
            "all_count": 0,
        }

    vehicles = result["vehicles"]

    if not vehicles:
        return {
            "ok": True,
            "status": "no_vehicle",
            "message": "亀21の該当方面の車両が近くに見つかりませんでした",
            "current_place": "近くの車両なし",
            "stop_name": "近くの車両なし",
            "stop_count": "--",
            "goenji": "確認中",
            "vehicle_id": "--",
            "route_id": TARGET_ROUTE_ID,
            "trip_id": "--",
            "stop_id": "--",
            "distance_km": None,
            "target_count": 0,
            "all_count": result.get("all_count", 0),
        }

    target = vehicles[0]
    distance = target.get("distance_km")
    stop_name = target.get("stop_name") or "接近中"

    return {
        "ok": True,
        "status": "success",
        "message": "亀21のリアルタイム情報を取得しました",
        "direction": BUS_TIMES[direction_key]["label"],
        "current_place": stop_name,
        "stop_name": stop_name,
        "stop_count": get_stop_count_text(distance),
        "goenji": get_goenji_text(distance),
        "vehicle_id": target.get("vehicle_id") or target.get("entity_id") or "--",
        "route_id": target.get("route_id") or "--",
        "trip_id": target.get("trip_id") or "--",
        "stop_id": target.get("stop_id") or "--",
        "latitude": target.get("latitude"),
        "longitude": target.get("longitude"),
        "distance_km": distance,
        "target_count": len(vehicles),
        "all_count": result.get("all_count", 0),
        "stops_loaded": len(STOP_NAMES),
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

    route_058 = [
        v for v in vehicles
        if v.get("route_id") == TARGET_ROUTE_ID
    ]

    route_058_sorted = sorted(
        route_058,
        key=lambda v: v["distance_km"] if v.get("distance_km") is not None else 9999
    )

    return jsonify({
        "ok": realtime["ok"],
        "reason": realtime["reason"],
        "stops_file_exists": os.path.exists(STOPS_FILE),
        "stops_loaded": len(STOP_NAMES),
        "target": {
            "name": "竪川大橋北詰",
            "latitude": TARGET_LAT,
            "longitude": TARGET_LON,
            "search_radius_km": SEARCH_RADIUS_KM,
            "target_route_id": TARGET_ROUTE_ID,
        },
        "all_count": len(vehicles),
        "route_058_count": len(route_058),
        "route_058_sample": route_058_sorted[:20],
    })


@app.route("/api/realtime-debug/<direction>")
def realtime_debug_direction(direction):
    if direction not in BUS_TIMES:
        return jsonify({"error": "invalid direction"}), 404

    result = get_target_vehicles(direction)

    return jsonify({
        "ok": result["ok"],
        "reason": result["reason"],
        "direction": direction,
        "direction_label": BUS_TIMES[direction]["label"],
        "stops_file_exists": os.path.exists(STOPS_FILE),
        "stops_loaded": len(STOP_NAMES),
        "count": len(result.get("vehicles", [])),
        "vehicles": result.get("vehicles", []),
    })


if __name__ == "__main__":
    app.run(debug=True)