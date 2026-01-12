"""Data update coordinator for Cardmarket integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CardmarketScraper, CardmarketError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CardmarketDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Cardmarket data."""

    def __init__(
        self,
        hass: HomeAssistant,
        scraper: CardmarketScraper,
        tracked_cards: list[dict[str, Any]] | None = None,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.scraper = scraper
        self.tracked_cards = tracked_cards or []

    def update_tracked_cards(self, cards: list[dict[str, Any]]) -> None:
        """Update the list of tracked cards."""
        self.tracked_cards = cards

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Cardmarket website."""
        try:
            # Get all account/order data
            data = await self.scraper.get_all_data()
            
            # Get tracked card prices if any cards are being tracked
            if self.tracked_cards:
                tracked_cards = await self.scraper.get_tracked_card_prices(
                    self.tracked_cards
                )
                data["tracked_cards"] = tracked_cards
            else:
                data["tracked_cards"] = {}
            
            return data

        except CardmarketError as err:
            raise UpdateFailed(f"Error fetching data from Cardmarket: {err}") from err
