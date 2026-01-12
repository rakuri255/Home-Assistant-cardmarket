"""Config flow for Cardmarket integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import CardmarketScraper, CardmarketAuthError, CardmarketConnectionError
from .const import (
    CONF_GAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TRACKED_CARDS,
    CONF_USERNAME,
    DEFAULT_GAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUPPORTED_GAMES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_GAME, default=DEFAULT_GAME): vol.In(SUPPORTED_GAMES),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL // 60): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL // 60, max=MAX_SCAN_INTERVAL // 60)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    scraper = CardmarketScraper(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        game=data.get(CONF_GAME, DEFAULT_GAME),
    )

    try:
        logged_in = await scraper.login()
        if not logged_in:
            raise InvalidAuth("Login failed")
    except CardmarketAuthError as err:
        await scraper.close()
        raise InvalidAuth from err
    except CardmarketConnectionError as err:
        await scraper.close()
        raise CannotConnect from err
    finally:
        await scraper.close()

    username = data[CONF_USERNAME]
    game = data.get(CONF_GAME, DEFAULT_GAME)
    game_name = SUPPORTED_GAMES.get(game, game)

    return {
        "title": f"Cardmarket {game_name} ({username})",
        "unique_id": f"{username.lower()}_{game.lower()}",
    }


class CardmarketConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cardmarket."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CardmarketOptionsFlowHandler:
        """Get the options flow for this handler."""
        return CardmarketOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CardmarketOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Cardmarket options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._search_results: list[dict[str, Any]] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["search_card", "manage_tracked"],
        )

    async def async_step_search_card(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle card search step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            search_term = user_input.get("search_term", "")
            
            if search_term:
                # Get API from hass.data
                if DOMAIN in self.hass.data:
                    for entry_id, data in self.hass.data[DOMAIN].items():
                        if "api" in data:
                            api = data["api"]
                            try:
                                self._search_results = await api.search_cards(
                                    search_term, max_results=20
                                )
                                if self._search_results:
                                    return await self.async_step_select_card()
                                else:
                                    errors["base"] = "no_results"
                            except Exception as err:
                                _LOGGER.error("Search failed: %s", err)
                                errors["base"] = "search_failed"
                            break

        return self.async_show_form(
            step_id="search_card",
            data_schema=vol.Schema(
                {
                    vol.Required("search_term"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_card(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle card selection step."""
        if user_input is not None:
            selected_url = user_input.get("card")
            
            if selected_url:
                # Find the card info
                for card in self._search_results:
                    if card.get("url") == selected_url:
                        # Add to tracked cards
                        current_tracked = list(
                            self.config_entry.options.get(CONF_TRACKED_CARDS, [])
                        )
                        
                        # Check if already tracked
                        if not any(c.get("url") == selected_url for c in current_tracked):
                            current_tracked.append({
                                "url": card.get("url"),
                                "name": card.get("name"),
                                "set": card.get("set", ""),
                            })
                            
                            return self.async_create_entry(
                                title="",
                                data={CONF_TRACKED_CARDS: current_tracked},
                            )
                        else:
                            return self.async_abort(reason="already_tracked")
        
        # Build options from search results
        card_options = {
            card.get("url"): f"{card.get('name')} ({card.get('set', 'Unknown')})"
            for card in self._search_results
            if card.get("url")
        }

        return self.async_show_form(
            step_id="select_card",
            data_schema=vol.Schema(
                {
                    vol.Required("card"): vol.In(card_options),
                }
            ),
        )

    async def async_step_manage_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle managing tracked cards."""
        current_tracked = list(
            self.config_entry.options.get(CONF_TRACKED_CARDS, [])
        )

        if user_input is not None:
            cards_to_keep = user_input.get("tracked_cards", [])
            
            # Filter to only keep selected cards
            new_tracked = [
                card for card in current_tracked
                if card.get("url") in cards_to_keep
            ]
            
            return self.async_create_entry(
                title="",
                data={CONF_TRACKED_CARDS: new_tracked},
            )

        if not current_tracked:
            return self.async_abort(reason="no_tracked_cards")

        # Build multi-select options
        card_options = {
            card.get("url"): f"{card.get('name')} ({card.get('set', 'Unknown')})"
            for card in current_tracked
            if card.get("url")
        }
        
        # Default to all currently tracked
        default_selected = list(card_options.keys())

        return self.async_show_form(
            step_id="manage_tracked",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "tracked_cards",
                        default=default_selected,
                    ): vol.All(
                        cv.multi_select(card_options),
                    ),
                }
            ),
            description_placeholders={
                "count": str(len(current_tracked)),
            },
        )
