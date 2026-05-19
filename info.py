import requests

from datetime import datetime


def handle_info(text):

    text = text.lower().strip()

    # =========================================
    # TIME
    # =========================================

    TIME_WORDS = [
        "what time is it",
        "time"
    ]

    if any(word in text for word in TIME_WORDS):

        current_time = datetime.now().strftime("%H:%M")

        print(f"Current time is {current_time}")

        return True

    # =========================================
    # DATE
    # =========================================

    DATE_WORDS = [
        "what date is it",
        "date",
        "today"
    ]

    if any(word in text for word in DATE_WORDS):

        current_date = datetime.now().strftime("%d %B %Y")

        print(f"Today is {current_date}")

        return True

    # =========================================
    # WEATHER
    # =========================================

    WEATHER_WORDS = [
        "weather",
        "whether",
        "further",
        "visit",
        "waiter"
    ]

    if any(word in text for word in WEATHER_WORDS):

        city = "Baku"

        words = text.split()

        # weather in london
        if "in" in words:

            index = words.index("in")

            if index + 1 < len(words):

                city = words[index + 1]

        try:

            url = f"https://wttr.in/{city}?format=j1"

            response = requests.get(url)

            data = response.json()

            temp = data["current_condition"][0]["temp_C"]

            desc = data["current_condition"][0]["weatherDesc"][0]["value"]

            humidity = data["current_condition"][0]["humidity"]

            print(
                f"Weather in {city}: "
                f"{temp}°C, "
                f"{desc}, "
                f"Humidity {humidity}%"
            )

        except Exception as e:

            print("Weather data not found")
            print(e)

        return True

    return False