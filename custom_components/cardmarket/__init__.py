"""The Cardmarket integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import CardmarketScraper
from .const import (
    CONF_GAME,
    CONF_PASSWORD,
    CONF_TRACKED_CARDS,
    CONF_USERNAME,
    DEFAULT_GAME,
    DOMAIN,
)
from .coordinator import CardmarketDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cardmarket from a config entry."""
    scraper = CardmarketScraper(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        game=entry.data.get(CONF_GAME, DEFAULT_GAME),
    )

    # Get tracked cards from options
    tracked_cards = entry.options.get(CONF_TRACKED_CARDS, [])
    tracked_urls = [card.get("url") for card in tracked_cards if card.get("url")]

    coordinator = CardmarketDataUpdateCoordinator(
        hass, scraper, tracked_card_urls=tracked_urls
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": scraper,
        "scraper": scraper,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up services (only once)
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the scraper session
        scraper: CardmarketScraper = data.get("scraper")
        if scraper:
            await scraper.close()

        # Unload services if this was the last entry
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)

    return unload_ok
