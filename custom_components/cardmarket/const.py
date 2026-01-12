"""Constants for the Cardmarket integration."""

DOMAIN = "cardmarket"

# Configuration keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_GAME = "game"
CONF_TRACKED_CARDS = "tracked_cards"
CONF_SCAN_INTERVAL = "scan_interval"

# Supported games on Cardmarket
SUPPORTED_GAMES = {
    "Magic": "Magic: The Gathering",
    "Pokemon": "Pokémon",
    "YuGiOh": "Yu-Gi-Oh!",
    "OnePiece": "One Piece",
    "Lorcana": "Disney Lorcana",
    "FleshAndBlood": "Flesh and Blood",
    "StarWarsUnlimited": "Star Wars: Unlimited",
    "Digimon": "Digimon",
    "DragonBallSuper": "Dragon Ball Super",
    "Vanguard": "Cardfight!! Vanguard",
    "WeissSchwarz": "Weiß Schwarz",
    "FinalFantasy": "Final Fantasy TCG",
    "ForceOfWill": "Force of Will",
}

DEFAULT_GAME = "Magic"

# Website URLs
BASE_URL = "https://www.cardmarket.com"

# URL templates - {game} will be replaced with the game identifier
LOGIN_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/PostGetAction/User_Login"
SEARCH_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/Products/Singles"
STOCK_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/Stock"
SALES_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/Orders/Sales"
PURCHASES_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/Orders/Purchases"
MESSAGES_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}/Account/Messages"
GAME_URL_TEMPLATE = "https://www.cardmarket.com/en/{game}"

# Update intervals (in seconds)
DEFAULT_SCAN_INTERVAL = 3600  # 60 minutes
MIN_SCAN_INTERVAL = 300  # 5 minutes minimum
MAX_SCAN_INTERVAL = 86400  # 24 hours maximum

# Sensor types
SENSOR_ACCOUNT_BALANCE = "account_balance"
SENSOR_STOCK_COUNT = "stock_count"
SENSOR_STOCK_VALUE = "stock_value"
SENSOR_ORDERS_SELLER_PAID = "orders_seller_paid"
SENSOR_ORDERS_SELLER_SENT = "orders_seller_sent"
SENSOR_ORDERS_BUYER_PAID = "orders_buyer_paid"
SENSOR_ORDERS_BUYER_SENT = "orders_buyer_sent"
SENSOR_MESSAGES_UNREAD = "messages_unread"

# Attribute keys
ATTR_USERNAME = "username"
ATTR_GAME = "game"
ATTR_REPUTATION = "reputation"
ATTR_SELL_COUNT = "sell_count"
ATTR_SOLD_ITEMS = "sold_items"
ATTR_VACATION_STATUS = "vacation_status"
ATTR_CARD_NAME = "card_name"
ATTR_CARD_SET = "expansion"
ATTR_CARD_URL = "url"
ATTR_PRICE_FROM = "price_from"
ATTR_PRICE_TREND = "price_trend"
ATTR_PRICE_30_DAY = "price_30_day_avg"
ATTR_PRICE_7_DAY = "price_7_day_avg"
ATTR_PRICE_1_DAY = "price_1_day_avg"
ATTR_AVAILABLE_ITEMS = "available_items"

# Services
SERVICE_SEARCH_CARD = "search_card"
SERVICE_ADD_TRACKED_CARD = "add_tracked_card"
SERVICE_REMOVE_TRACKED_CARD = "remove_tracked_card"
