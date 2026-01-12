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
        tracked_card_urls: list[str] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.scraper = scraper
        self.tracked_card_urls = tracked_card_urls or []

    def update_tracked_cards(self, urls: list[str]) -> None:
        """Update the list of tracked card URLs."""
        self.tracked_card_urls = urls

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Cardmarket website."""
        try:
            # Get all account/order data
            data = await self.scraper.get_all_data()
            
            # Get tracked card prices if any cards are being tracked
            if self.tracked_card_urls:
                tracked_cards = await self.scraper.get_tracked_card_prices(
                    self.tracked_card_urls
                )
                data["tracked_cards"] = tracked_cards
            else:
                data["tracked_cards"] = {}
            
            return data

        except CardmarketError as err:
            raise UpdateFailed(f"Error fetching data from Cardmarket: {err}") from err
