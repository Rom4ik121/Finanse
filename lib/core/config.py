"""Application configuration, paths, and shared constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

try:
    from platformdirs import user_data_dir
except ImportError:  # pragma: no cover - fallback when platformdirs is absent
    user_data_dir = None  # type: ignore[assignment]


APP_NAME: Final[str] = "finanse"
APP_AUTHOR: Final[str] = "finanse"

DEFAULT_CURRENCY: Final[str] = "RUB"
DEFAULT_THEME: Final[str] = "dark"
DEFAULT_LANGUAGE: Final[str] = "ru"
DEFAULT_EXCHANGE_UPDATE_INTERVAL_MINUTES: Final[int] = 60

# Money precision
MONEY_QUANTIZE: Final[str] = "0.01"
# Exchange rates need many decimals (e.g. UZS→BTC can be ~1e-12).
FIAT_RATE_QUANTIZE: Final[str] = "0.00000000000001"
CRYPTO_RATE_QUANTIZE: Final[str] = "0.00000000000001"

DEFAULT_CATEGORIES: Final[tuple[str, ...]] = (
    "Еда",
    "Транспорт",
    "Жильё",
    "Коммунальные",
    "Здоровье",
    "Развлечения",
    "Одежда",
    "Образование",
    "Зарплата",
    "Подарки",
    "Накопление",
    "Savings",
    "Инвестиции",
    "Прочее",
)

# Display metadata for account UI (icons / palette keys).
# Currency / crypto glyphs use keys ``ccy_USD``, ``ccy_BTC`` (built from catalog).
ACCOUNT_ICON_GROUPS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        "icon_group.finance",
        (
            "wallet",
            "account_balance_wallet",
            "credit_card",
            "payments",
            "attach_money",
            "monetization_on",
            "savings",
            "account_balance",
            "currency_exchange",
            "paid",
            "sell",
            "request_quote",
            "receipt_long",
            "price_check",
            "trending_up",
            "show_chart",
            "atm",
            "contactless",
            "qr_code_2",
            "safe",
            "point_of_sale",
            "token",
            "generating_tokens",
        ),
    ),
    (
        "icon_group.cards",
        (
            "credit_card",
            "contactless",
            "account_balance_wallet",
            "wallet",
            "payments",
            "paid",
            "redeem",
            "card_giftcard",
            "loyalty",
            "style",
        ),
    ),
    (
        "icon_group.shopping",
        (
            "store",
            "storefront",
            "shopping_cart",
            "shopping_bag",
            "shopping_basket",
            "local_mall",
            "local_offer",
            "inventory_2",
            "diamond",
            "sell",
        ),
    ),
    (
        "icon_group.travel",
        (
            "flight",
            "flight_takeoff",
            "directions_car",
            "directions_bus",
            "train",
            "local_taxi",
            "two_wheeler",
            "local_shipping",
            "map",
            "public",
            "beach_access",
            "luggage",
            "hotel",
        ),
    ),
    (
        "icon_group.home",
        (
            "home",
            "apartment",
            "cottage",
            "work",
            "business_center",
            "school",
            "fitness_center",
            "local_cafe",
            "restaurant",
            "pets",
            "child_care",
        ),
    ),
    (
        "icon_group.tech",
        (
            "smartphone",
            "laptop",
            "computer",
            "cloud",
            "wifi",
            "headphones",
            "bolt",
            "qr_code_2",
        ),
    ),
    (
        "icon_group.other",
        (
            "person",
            "groups",
            "handshake",
            "star",
            "favorite",
            "emoji_events",
            "eco",
            "palette",
            "brush",
            "camera_alt",
            "celebration",
            "volunteer_activism",
            "apps",
            "more_horiz",
        ),
    ),
)

# Flat thematic icons (currency glyphs appended at runtime in the picker).
ACCOUNT_ICONS: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(
        icon for _label, icons in ACCOUNT_ICON_GROUPS for icon in icons
    )
)

ACCOUNT_COLORS: Final[tuple[str, ...]] = (
    "#00897B",
    "#2E7D32",
    "#43A047",
    "#7CB342",
    "#C0CA33",
    "#F9A825",
    "#FF8F00",
    "#EF6C00",
    "#E65100",
    "#D84315",
    "#C62828",
    "#AD1457",
    "#6A1B9A",
    "#4527A0",
    "#283593",
    "#1565C0",
    "#0277BD",
    "#00838F",
    "#00695C",
    "#37474F",
    "#455A64",
    "#546E7A",
    "#5D4037",
    "#795548",
    "#F4511E",
    "#FB8C00",
    "#FDD835",
    "#9CCC65",
    "#26A69A",
    "#26C6DA",
    "#42A5F5",
    "#5C6BC0",
    "#7E57C2",
    "#AB47BC",
    "#EC407A",
    "#EF5350",
    "#FF7043",
    "#8BC34A",
    "#00ACC1",
    "#FFD54F",
)

# Large palette for category / account icon pickers.
CATEGORY_COLORS: Final[tuple[str, ...]] = (
    "#00897B",
    "#2E7D32",
    "#43A047",
    "#7CB342",
    "#C0CA33",
    "#F9A825",
    "#FF8F00",
    "#EF6C00",
    "#E65100",
    "#D84315",
    "#C62828",
    "#AD1457",
    "#6A1B9A",
    "#4527A0",
    "#283593",
    "#1565C0",
    "#0277BD",
    "#00838F",
    "#00695C",
    "#37474F",
    "#455A64",
    "#546E7A",
    "#5D4037",
    "#795548",
    "#8D6E63",
    "#F4511E",
    "#FB8C00",
    "#FDD835",
    "#FFD54F",
    "#9CCC65",
    "#26A69A",
    "#26C6DA",
    "#42A5F5",
    "#5C6BC0",
    "#7E57C2",
    "#AB47BC",
    "#EC407A",
    "#EF5350",
    "#FF7043",
    "#8BC34A",
    "#00ACC1",
)

# Grouped icon keys for the category picker (label key → icons).
# Keys are stored in DB; mapped to Flet Icons in presentation.icon_registry.
CATEGORY_ICON_GROUPS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        "icon_group.food",
        (
            "restaurant",
            "fastfood",
            "local_cafe",
            "coffee",
            "local_bar",
            "liquor",
            "cake",
            "bakery_dining",
            "ramen_dining",
            "icecream",
            "local_pizza",
            "set_meal",
            "lunch_dining",
            "dinner_dining",
            "takeout_dining",
            "kebab_dining",
            "brunch_dining",
            "kitchen",
            "egg",
            "restaurant_menu",
        ),
    ),
    (
        "icon_group.shopping",
        (
            "shopping_cart",
            "shopping_bag",
            "shopping_basket",
            "store",
            "storefront",
            "local_grocery_store",
            "local_mall",
            "local_offer",
            "sell",
            "checkroom",
            "diamond",
            "watch",
            "card_giftcard",
            "redeem",
            "inventory_2",
        ),
    ),
    (
        "icon_group.transport",
        (
            "directions_car",
            "directions_bus",
            "train",
            "subway",
            "tram",
            "flight",
            "flight_takeoff",
            "local_taxi",
            "two_wheeler",
            "directions_bike",
            "pedal_bike",
            "electric_scooter",
            "local_gas_station",
            "local_shipping",
            "directions_walk",
            "sailing",
            "directions_boat",
            "map",
            "public",
        ),
    ),
    (
        "icon_group.home",
        (
            "home",
            "apartment",
            "hotel",
            "cottage",
            "weekend",
            "chair",
            "bed",
            "kitchen",
            "electrical_services",
            "lightbulb",
            "water_drop",
            "wifi",
            "bolt",
            "local_fire_department",
            "cleaning_services",
            "handyman",
            "build",
            "local_laundry_service",
            "content_cut",
            "plumbing",
        ),
    ),
    (
        "icon_group.health",
        (
            "local_hospital",
            "medical_services",
            "healing",
            "medication",
            "monitor_heart",
            "fitness_center",
            "spa",
            "self_improvement",
            "psychology",
            "favorite",
            "emergency",
            "bloodtype",
        ),
    ),
    (
        "icon_group.entertainment",
        (
            "movie",
            "sports_esports",
            "music_note",
            "headphones",
            "theater_comedy",
            "sports_soccer",
            "sports_basketball",
            "sports_tennis",
            "casino",
            "nightlife",
            "celebration",
            "palette",
            "brush",
            "camera_alt",
            "photo_camera",
            "videogame_asset",
        ),
    ),
    (
        "icon_group.finance",
        (
            "payments",
            "attach_money",
            "savings",
            "account_balance",
            "account_balance_wallet",
            "credit_card",
            "monetization_on",
            "currency_exchange",
            "currency_bitcoin",
            "paid",
            "trending_up",
            "show_chart",
            "receipt_long",
            "request_quote",
            "price_check",
            "point_of_sale",
            "atm",
            "contactless",
            "qr_code_2",
            "safe",
        ),
    ),
    (
        "icon_group.work",
        (
            "work",
            "business_center",
            "school",
            "menu_book",
            "laptop",
            "computer",
            "smartphone",
            "phone_android",
            "cloud",
            "mail",
            "print",
            "badge",
        ),
    ),
    (
        "icon_group.family",
        (
            "pets",
            "child_care",
            "baby_changing_station",
            "family_restroom",
            "groups",
            "person",
            "face",
            "handshake",
            "volunteer_activism",
            "diversity_3",
        ),
    ),
    (
        "icon_group.travel",
        (
            "flight",
            "luggage",
            "beach_access",
            "park",
            "local_florist",
            "eco",
            "wb_sunny",
            "nightlight",
            "umbrella",
            "forest",
            "hiking",
            "museum",
            "cabin",
            "terrain",
        ),
    ),
    (
        "icon_group.other",
        (
            "category",
            "category_outlined",
            "star",
            "emoji_events",
            "military_tech",
            "smoking_rooms",
            "bolt",
            "favorite",
            "more_horiz",
            "apps",
        ),
    ),
)

# Flat list kept for seeds / validation / fallbacks.
CATEGORY_ICONS: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(
        icon for _label, icons in CATEGORY_ICON_GROUPS for icon in icons
    )
)

SAVINGS_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"Накопление", "Savings", "Jamg‘arma", "Jamg'arma"}
)

# Default seed: (name, kind, icon, color)
DEFAULT_CATEGORY_SEED: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("Еда", "expense", "restaurant", "#EF6C00"),
    ("Транспорт", "expense", "directions_car", "#1565C0"),
    ("Жильё", "expense", "home", "#5D4037"),
    ("Коммунальные", "expense", "electrical_services", "#00838F"),
    ("Здоровье", "expense", "local_hospital", "#C62828"),
    ("Развлечения", "expense", "movie", "#6A1B9A"),
    ("Одежда", "expense", "checkroom", "#AD1457"),
    ("Образование", "expense", "school", "#283593"),
    ("Зарплата", "income", "payments", "#2E7D32"),
    ("Подарки", "both", "card_giftcard", "#C0CA33"),
    ("Накопление", "both", "savings", "#00897B"),
    ("Инвестиции", "both", "trending_up", "#4527A0"),
    ("Прочее", "both", "category", "#546E7A"),
)


def _default_data_dir() -> Path:
    """Resolve the application data directory under the user profile."""
    if user_data_dir is not None:
        path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    else:
        path = Path.home() / f".{APP_NAME}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(slots=True)
class NotificationSettings:
    """User-facing notification preferences."""

    enabled: bool = True
    subscription_reminders: bool = True
    debt_reminders: bool = True
    goal_milestones: bool = True
    low_balance_threshold: float | None = None


@dataclass(slots=True)
class AppConfig:
    """Runtime application settings and filesystem paths.

    Paths default to a per-user data directory (platformdirs when available,
    otherwise ``~/.finanse``).
    """

    data_dir: Path = field(default_factory=_default_data_dir)
    default_currency: str = DEFAULT_CURRENCY
    theme: str = DEFAULT_THEME
    language: str = DEFAULT_LANGUAGE
    exchange_update_interval_minutes: int = DEFAULT_EXCHANGE_UPDATE_INTERVAL_MINUTES
    notifications: NotificationSettings = field(default_factory=NotificationSettings)

    # API key placeholders (filled from env / secrets store later)
    exchange_rate_api_key: str | None = None
    crypto_api_key: str | None = None
    openai_api_key: str | None = None

    @property
    def db_path(self) -> Path:
        """SQLite database file path."""
        return self.data_dir / "finanse.db"

    @property
    def database_url(self) -> str:
        """SQLAlchemy SQLite URL for the local database."""
        return f"sqlite:///{self.db_path.as_posix()}"

    @property
    def backup_dir(self) -> Path:
        """Directory for database backups."""
        path = self.data_dir / "backups"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def export_dir(self) -> Path:
        """Directory for exported reports and data dumps."""
        path = self.data_dir / "exports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_dir(self) -> Path:
        """Directory for application log files."""
        path = self.data_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_directories(self) -> None:
        """Create data, backup, export, and log directories if missing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def get_default_config() -> AppConfig:
    """Build a default :class:`AppConfig` with directories ensured."""
    config = AppConfig()
    config.ensure_directories()
    return config
