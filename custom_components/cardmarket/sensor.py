"""Sensor platform for Cardmarket integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_REPUTATION,
    ATTR_SELL_COUNT,
    ATTR_SOLD_ITEMS,
    ATTR_USERNAME,
    ATTR_VACATION_STATUS,
    DOMAIN,
)
from .coordinator import CardmarketDataUpdateCoordinator


@dataclass(frozen=True)
class CardmarketSensorEntityDescriptionMixin:
    """Mixin for Cardmarket sensor entity description."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None


@dataclass(frozen=True)
class CardmarketSensorEntityDescription(
    SensorEntityDescription, CardmarketSensorEntityDescriptionMixin
):
    """Describe Cardmarket sensor entity."""


def get_account_balance(data: dict[str, Any]) -> float | None:
    """Get account balance from data."""
    account = data.get("account", {})
    return account.get("balance", 0.0)


def get_account_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Get account attributes."""
    account = data.get("account", {})
    attrs = {}
    
    if username := account.get("username"):
        attrs[ATTR_USERNAME] = username
    if reputation := account.get("reputation"):
        attrs[ATTR_REPUTATION] = reputation
    if sell_count := account.get("sell_count"):
        attrs[ATTR_SELL_COUNT] = sell_count
    if sold_items := account.get("sold_items"):
        attrs[ATTR_SOLD_ITEMS] = sold_items

    return attrs


SENSOR_DESCRIPTIONS: tuple[CardmarketSensorEntityDescription, ...] = (
    CardmarketSensorEntityDescription(
        key="account_balance",
        translation_key="account_balance",
        name="Account Balance",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=get_account_balance,
        attributes_fn=get_account_attributes,
    ),
    CardmarketSensorEntityDescription(
        key="stock_count",
        translation_key="stock_count",
        name="Stock Articles",
        native_unit_of_measurement="articles",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cards",
        value_fn=lambda data: data.get("stock_count", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="stock_value",
        translation_key="stock_value",
        name="Stock Value",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: round(data.get("stock_value", 0.0), 2),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="seller_orders_paid",
        translation_key="seller_orders_paid",
        name="Seller Orders (Paid)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:package-variant",
        value_fn=lambda data: data.get("seller_orders_paid", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="seller_orders_sent",
        translation_key="seller_orders_sent",
        name="Seller Orders (Sent)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:package-variant-closed",
        value_fn=lambda data: data.get("seller_orders_sent", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="seller_orders_arrived",
        translation_key="seller_orders_arrived",
        name="Seller Orders (Arrived)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:package-check",
        value_fn=lambda data: data.get("seller_orders_arrived", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="buyer_orders_paid",
        translation_key="buyer_orders_paid",
        name="Buyer Orders (Paid)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cart",
        value_fn=lambda data: data.get("buyer_orders_paid", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="buyer_orders_sent",
        translation_key="buyer_orders_sent",
        name="Buyer Orders (Sent)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:truck-delivery",
        value_fn=lambda data: data.get("buyer_orders_sent", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="buyer_orders_arrived",
        translation_key="buyer_orders_arrived",
        name="Buyer Orders (Arrived)",
        native_unit_of_measurement="orders",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:package-check",
        value_fn=lambda data: data.get("buyer_orders_arrived", 0),
        attributes_fn=None,
    ),
    CardmarketSensorEntityDescription(
        key="unread_messages",
        translation_key="unread_messages",
        name="Unread Messages",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:message-badge",
        value_fn=lambda data: data.get("unread_messages", 0),
        attributes_fn=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cardmarket sensors from a config entry."""
    coordinator: CardmarketDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    # Add standard sensors
    async_add_entities(
        CardmarketSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )

    # Add tracked card sensors
    from .card_sensor import async_setup_tracked_card_sensors
    await async_setup_tracked_card_sensors(hass, entry, async_add_entities, coordinator)


class CardmarketSensor(
    CoordinatorEntity[CardmarketDataUpdateCoordinator], SensorEntity
):
    """Representation of a Cardmarket sensor."""

    entity_description: CardmarketSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CardmarketDataUpdateCoordinator,
        entry: ConfigEntry,
        description: CardmarketSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Get username from coordinator data if available
        account = coordinator.data.get("account", {}) if coordinator.data else {}
        username = account.get("username", "Cardmarket")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Cardmarket {username}",
            manufacturer="Cardmarket",
            model="Web Scraper",
            entry_type=None,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.coordinator.data is None:
            return None
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
