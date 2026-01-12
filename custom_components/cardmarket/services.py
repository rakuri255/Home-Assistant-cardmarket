"""Services for Cardmarket integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_TRACKED_CARDS,
    DOMAIN,
    SERVICE_ADD_TRACKED_CARD,
    SERVICE_REMOVE_TRACKED_CARD,
    SERVICE_SEARCH_CARD,
)

_LOGGER = logging.getLogger(__name__)

SEARCH_CARD_SCHEMA = vol.Schema(
    {
        vol.Required("search_term"): cv.string,
        vol.Optional("max_results", default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=50)
        ),
    }
)

ADD_TRACKED_CARD_SCHEMA = vol.Schema(
    {
        vol.Required("card_url"): cv.string,
        vol.Required("card_name"): cv.string,
        vol.Optional("card_set", default=""): cv.string,
    }
)

REMOVE_TRACKED_CARD_SCHEMA = vol.Schema(
    {
        vol.Required("card_url"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Cardmarket integration."""

    async def handle_search_card(call: ServiceCall) -> dict[str, Any]:
        """Handle the search_card service call."""
        search_term = call.data["search_term"]
        max_results = call.data.get("max_results", 10)
        
        # Get the first configured entry's API
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if "api" in data:
                api = data["api"]
                results = await api.search_cards(search_term, max_results)
                
                # Fire an event with the search results
                hass.bus.async_fire(
                    f"{DOMAIN}_search_results",
                    {
                        "search_term": search_term,
                        "results": results,
                    }
                )
                
                _LOGGER.info(
                    "Card search for '%s' returned %d results",
                    search_term,
                    len(results),
                )
                
                return {"results": results}
        
        _LOGGER.error("No Cardmarket API available for search")
        return {"results": [], "error": "No API available"}

    async def handle_add_tracked_card(call: ServiceCall) -> None:
        """Handle the add_tracked_card service call."""
        card_url = call.data["card_url"]
        card_name = call.data["card_name"]
        card_set = call.data.get("card_set", "")
        
        # Get the first configured entry
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry:
                # Get current tracked cards from options
                current_options = dict(entry.options)
                tracked_cards = list(current_options.get(CONF_TRACKED_CARDS, []))
                
                # Check if card is already tracked
                for card in tracked_cards:
                    if card.get("url") == card_url:
                        _LOGGER.info("Card %s is already being tracked", card_name)
                        return
                
                # Add the new card
                tracked_cards.append({
                    "url": card_url,
                    "name": card_name,
                    "set": card_set,
                })
                
                # Update options
                current_options[CONF_TRACKED_CARDS] = tracked_cards
                hass.config_entries.async_update_entry(entry, options=current_options)
                
                _LOGGER.info("Added card to tracking: %s (%s)", card_name, card_set)
                
                # Trigger a coordinator refresh
                if "coordinator" in data:
                    await data["coordinator"].async_request_refresh()
                
                return
        
        _LOGGER.error("No Cardmarket entry found to add tracked card")

    async def handle_remove_tracked_card(call: ServiceCall) -> None:
        """Handle the remove_tracked_card service call."""
        card_url = call.data["card_url"]
        
        # Get the first configured entry
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry:
                # Get current tracked cards from options
                current_options = dict(entry.options)
                tracked_cards = list(current_options.get(CONF_TRACKED_CARDS, []))
                
                # Find and remove the card
                original_count = len(tracked_cards)
                tracked_cards = [c for c in tracked_cards if c.get("url") != card_url]
                
                if len(tracked_cards) < original_count:
                    # Update options
                    current_options[CONF_TRACKED_CARDS] = tracked_cards
                    hass.config_entries.async_update_entry(entry, options=current_options)
                    
                    _LOGGER.info("Removed card from tracking: %s", card_url)
                else:
                    _LOGGER.warning("Card not found in tracked cards: %s", card_url)
                
                return
        
        _LOGGER.error("No Cardmarket entry found to remove tracked card")

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_CARD,
        handle_search_card,
        schema=SEARCH_CARD_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TRACKED_CARD,
        handle_add_tracked_card,
        schema=ADD_TRACKED_CARD_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_TRACKED_CARD,
        handle_remove_tracked_card,
        schema=REMOVE_TRACKED_CARD_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Cardmarket services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEARCH_CARD)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TRACKED_CARD)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_TRACKED_CARD)
