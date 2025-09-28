from flask import Flask, request, jsonify
import swisseph as swe
import pytz
from timezonefinder import TimezoneFinder
from datetime import datetime
import os

app = Flask(__name__)

# Путь к эфемеридам
EPHE_PATH = os.path.join(os.path.dirname(__file__), 'ephemeris')
swe.set_ephe_path(EPHE_PATH)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        date_str = data['date']      # DD.MM.YYYY
        time_str = data['time']      # HH:MM
        lat = float(data['latitude'])
        lon = float(data['longitude'])

        # Определяем часовой пояс по координатам
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lon)
        if not tz_name:
            return jsonify({"error": "Не удалось определить часовой пояс"}), 400

        tz = pytz.timezone(tz_name)
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        dt_local = tz.localize(dt)
        dt_utc = dt_local.astimezone(pytz.utc)

        # Юлианский день
        jd = swe.utc_to_jd(dt_utc.year, dt_utc.month, dt_utc.day,
                           dt_utc.hour, dt_utc.minute, 0, 1)[1]

        # Джйотиш: асцендент и накшатра (с ayanamsa Лахири)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        houses = swe.houses(jd, lat, lon)
        asc = houses[0][0]
        moon = swe.calc(jd, swe.MOON)[0][0]
        nakshatra = int(moon / 13.3333)
        nakshatra_names = [
            "Ашвини", "Бхарани", "Криттика", "Рохини", "Мригашира", "Ардра", "Пунарвасу",
            "Пушья", "Ашлеша", "Магха", "Пурва Пхалгуни", "Уттара Пхалгуни", "Хаста",
            "Читра", "Свати", "Вишакха", "Анурадха", "Джештха", "Мула", "Пурва Ашадха",
            "Уттара Ашадха", "Шравана", "Дхаништха", "Шатабхиша", "Пурва Бхадрапада",
            "Уттара Бхадрапада", "Ревати"
        ]

        # Human Design: тропическое Солнце → врата
        sun_tropical = swe.calc_ut(jd, swe.SUN, flag=swe.FLG_J2000)[0][0]
        gate = int(sun_tropical / 5.625) + 1

        return jsonify({
            "jyotish": {
                "ascendant_deg": round(asc, 2),
                "moon_nakshatra": nakshatra_names[nakshatra] if 0 <= nakshatra < 27 else "Ошибка"
            },
            "human_design": {
                "sun_gate": gate,
                "sun_deg": round(sun_tropical, 2)
            },
            "meta": {
                "timezone_detected": tz_name,
                "julian_day": jd
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/health')
def health():
    return "OK"
