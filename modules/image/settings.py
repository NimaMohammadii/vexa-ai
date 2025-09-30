"""Configuration for the image generation flow."""

STATE_WAIT_PROMPT = "image:wait_prompt"
STATE_PROCESSING = "image:processing"
CREDIT_COST = 5
POLL_INTERVAL = 3.0
POLL_TIMEOUT = 300

DEFAULT_SIZE_KEY = "square"

# Runway supports a handful of predefined aspect ratios.  The values below map the
# human readable keys that are exposed in the Telegram bot to the ratio string that
# must be sent to Runway alongside some metadata used for localisation.
IMAGE_SIZE_OPTIONS = {
    "square": {
        "ratio": "1024:1024",
        "ratio_display": "1:1",
        "resolution_display": "1024×1024",
        "label_key": "image_size_square",
    },
    "landscape": {
        "ratio": "1344:768",
        "ratio_display": "16:9",
        "resolution_display": "1344×768",
        "label_key": "image_size_landscape",
    },
    "portrait": {
        "ratio": "768:1344",
        "ratio_display": "9:16",
        "resolution_display": "768×1344",
        "label_key": "image_size_portrait",
    },
    "classic": {
        "ratio": "1024:768",
        "ratio_display": "4:3",
        "resolution_display": "1024×768",
        "label_key": "image_size_classic",
    },
}

IMAGE_SIZE_ORDER = ("square", "landscape", "portrait", "classic")


def get_ratio_for_size(size_key: str) -> str:
    """Return the Runway ratio string for the provided size key."""

    option = IMAGE_SIZE_OPTIONS.get(size_key)
    if option:
        return option["ratio"]
    return IMAGE_SIZE_OPTIONS[DEFAULT_SIZE_KEY]["ratio"]
