"""Card price tracking sensors for Cardmarket integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVAILABLE_ITEMS,
    ATTR_CARD_NAME,
    ATTR_CARD_SET,
    ATTR_CARD_URL,
    ATTR_PRICE_1_DAY,
    ATTR_PRICE_7_DAY,
    ATTR_PRICE_30_DAY,
    ATTR_PRICE_FROM,
    ATTR_PRICE_TREND,
    CONF_TRACKED_CARDS,
    DOMAIN,
)
from .coordinator import CardmarketDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class CardmarketCardPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tracking a single card's price."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "€"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: CardmarketDataUpdateCoordinator,
        card_url: str,
        card_name: str,
        card_set: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the card price sensor."""
        super().__init__(coordinator)
        
        self._card_url = card_url
        self._card_name = card_name
        self._card_set = card_set
        self._entry = entry
        
        # Create a unique ID based on the card URL
        safe_id = card_url.replace("/", "_").replace(":", "").replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_card_{safe_id}"
        
        # Set the entity name
        self._attr_name = f"{card_name} ({card_set})" if card_set else card_name
        self._attr_icon = "mdi:cards"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Cardmarket",
            manufacturer="Cardmarket",
        )

    @property
    def native_value(self) -> float | None:
        """Return the card's current lowest price."""
        if not self.coordinator.data:
            return None
        
        tracked_cards = self.coordinator.data.get("tracked_cards", {})
        card_data = tracked_cards.get(self._card_url, {})
        
        return card_data.get("price_from")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        tracked_cards = self.coordinator.data.get("tracked_cards", {})
        card_data = tracked_cards.get(self._card_url, {})
        
        attrs = {
            ATTR_CARD_NAME: self._card_name,
            ATTR_CARD_SET: self._card_set,
            ATTR_CARD_URL: self._card_url,
        }
        
        if price_from := card_data.get("price_from"):
            attrs[ATTR_PRICE_FROM] = price_from
        if price_trend := card_data.get("price_trend"):
            attrs[ATTR_PRICE_TREND] = price_trend
        if price_30 := card_data.get("price_30_day_avg"):
            attrs[ATTR_PRICE_30_DAY] = price_30
        if price_7 := card_data.get("price_7_day_avg"):
            attrs[ATTR_PRICE_7_DAY] = price_7
        if price_1 := card_data.get("price_1_day_avg"):
            attrs[ATTR_PRICE_1_DAY] = price_1
        if available := card_data.get("available_items"):
            attrs[ATTR_AVAILABLE_ITEMS] = available
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data:
            return False
        
        tracked_cards = self.coordinator.data.get("tracked_cards", {})
        card_data = tracked_cards.get(self._card_url, {})
        
        return "error" not in card_data


async def async_setup_tracked_card_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    coordinator: CardmarketDataUpdateCoordinator,
) -> None:
    """Set up sensors for tracked cards."""
    tracked_cards = entry.options.get(CONF_TRACKED_CARDS, [])
    
    if not tracked_cards:
        return
    
    entities = []
    
    for card in tracked_cards:
        card_url = card.get("url", "")
        card_name = card.get("name", "Unknown Card")
        card_set = card.get("set", "")
        
        if card_url:
            entities.append(
                CardmarketCardPriceSensor(
                    coordinator=coordinator,
                    card_url=card_url,
                    card_name=card_name,
                    card_set=card_set,
                    entry=entry,
                )
            )
    
    if entities:
        async_add_entities(entities)
