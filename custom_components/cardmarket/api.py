"""Cardmarket Web Scraper for fetching data from cardmarket.com."""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import cloudscraper
from bs4 import BeautifulSoup

from .const import (
    BASE_URL,
    DEFAULT_GAME,
    GAME_URL_TEMPLATE,
    LOGIN_URL_TEMPLATE,
    MESSAGES_URL_TEMPLATE,
    PURCHASES_URL_TEMPLATE,
    SALES_URL_TEMPLATE,
    SEARCH_URL_TEMPLATE,
    STOCK_URL_TEMPLATE,
    SUPPORTED_GAMES,
)

_LOGGER = logging.getLogger(__name__)


class CardmarketError(Exception):
    """Base exception for Cardmarket errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message


class CardmarketAuthError(CardmarketError):
    """Exception for authentication errors."""


class CardmarketConnectionError(CardmarketError):
    """Exception for connection errors."""


class CardmarketScraper:
    """Cardmarket Web Scraper client using cloudscraper to bypass Cloudflare."""

    def __init__(
        self,
        username: str,
        password: str,
        game: str = DEFAULT_GAME,
    ) -> None:
        """Initialize the scraper client."""
        self._username = username
        self._password = password
        self._game = game if game in SUPPORTED_GAMES else DEFAULT_GAME
        self._scraper: cloudscraper.CloudScraper | None = None
        self._logged_in = False
        self._executor = ThreadPoolExecutor(max_workers=1)

    @property
    def game(self) -> str:
        """Return the current game."""
        return self._game

    @property
    def game_name(self) -> str:
        """Return the display name of the current game."""
        return SUPPORTED_GAMES.get(self._game, self._game)

    def _get_url(self, template: str) -> str:
        """Get a URL with the game substituted."""
        return template.format(game=self._game)

    def _get_scraper(self) -> cloudscraper.CloudScraper:
        """Get or create cloudscraper session."""
        if self._scraper is None:
            self._scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
        return self._scraper

    async def close(self) -> None:
        """Close the session."""
        if self._scraper:
            self._scraper.close()
            self._scraper = None
            self._logged_in = False
        self._executor.shutdown(wait=False)

    def _sync_login(self) -> bool:
        """Synchronous login to Cardmarket."""
        scraper = self._get_scraper()

        try:
            # First, get the login page to obtain CSRF token
            game_url = self._get_url(GAME_URL_TEMPLATE)
            response = scraper.get(game_url)
            if response.status_code != 200:
                raise CardmarketConnectionError(
                    f"Failed to load Cardmarket page: {response.status_code}"
                )

            # Parse the page for CSRF token
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_input = soup.find("input", {"name": "__cmtkn"})
            csrf_token = csrf_input.get("value") if csrf_input else None

            # Perform login
            login_data = {
                "username": self._username,
                "userPassword": self._password,
                "referalPage": f"/en/{self._game}",
            }

            if csrf_token:
                login_data["__cmtkn"] = csrf_token

            login_url = self._get_url(LOGIN_URL_TEMPLATE)
            response = scraper.post(login_url, data=login_data)

            if response.status_code != 200:
                raise CardmarketAuthError(
                    f"Login failed with status: {response.status_code}"
                )

            # Check if login was successful
            if self._username.lower() in response.text.lower():
                self._logged_in = True
                _LOGGER.debug("Successfully logged in to Cardmarket")
                return True

            raise CardmarketAuthError("Login failed - invalid credentials")

        except cloudscraper.exceptions.CloudflareChallengeError as err:
            raise CardmarketConnectionError(f"Cloudflare challenge failed: {err}") from err
        except Exception as err:
            if isinstance(err, (CardmarketAuthError, CardmarketConnectionError)):
                raise
            raise CardmarketConnectionError(f"Connection error: {err}") from err

    async def login(self) -> bool:
        """Log in to Cardmarket (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._sync_login)

    async def _ensure_logged_in(self) -> None:
        """Ensure we are logged in."""
        if not self._logged_in:
            await self.login()

    def _sync_get_page(self, url: str) -> str:
        """Synchronously get a page."""
        scraper = self._get_scraper()
        response = scraper.get(url)
        if response.status_code != 200:
            raise CardmarketConnectionError(f"Failed to load page: {response.status_code}")
        return response.text

    async def _get_page(self, url: str) -> str:
        """Get a page asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._sync_get_page, url)

    def _parse_balance_from_html(self, html: str) -> float:
        """Parse account balance from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Look for the balance in the header navigation
        # Pattern: <span id="totalCreditMainNav">(&nbsp;15,43 €&nbsp;)</span>
        balance_elem = soup.find(id="totalCreditMainNav")
        if balance_elem:
            balance_text = balance_elem.get_text()
            balance_match = re.search(r"(\d+[.,]\d{2})\s*€", balance_text)
            if balance_match:
                return float(balance_match.group(1).replace(",", "."))

        # Alternative: Look for any element with balance-like text
        for elem in soup.find_all(class_=re.compile(r"text-success", re.IGNORECASE)):
            text = elem.get_text()
            balance_match = re.search(r"(\d+[.,]\d{2})\s*€", text)
            if balance_match:
                return float(balance_match.group(1).replace(",", "."))

        return 0.0

    def _parse_order_counts_from_html(self, html: str) -> dict[str, int]:
        """Parse order counts from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        orders = {"paid": 0, "sent": 0, "arrived": 0}

        # Look for links with order status and count
        # Pattern: <a href="/en/Magic/Orders/Sales/Paid">Paid0</a>
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text().strip()

            if "/Paid" in href:
                # Extract number from text like "Paid0" or "Paid 0"
                match = re.search(r"Paid\s*(\d+)", text, re.IGNORECASE)
                if match:
                    orders["paid"] = int(match.group(1))
                else:
                    # Look for badge inside the link
                    badge = link.find(class_="badge")
                    if badge:
                        try:
                            orders["paid"] = int(badge.get_text().strip())
                        except ValueError:
                            pass

            elif "/Sent" in href:
                match = re.search(r"Sent\s*(\d+)", text, re.IGNORECASE)
                if match:
                    orders["sent"] = int(match.group(1))
                else:
                    badge = link.find(class_="badge")
                    if badge:
                        try:
                            orders["sent"] = int(badge.get_text().strip())
                        except ValueError:
                            pass

            elif "/Arrived" in href:
                match = re.search(r"Arrived\s*(\d+)", text, re.IGNORECASE)
                if match:
                    orders["arrived"] = int(match.group(1))
                else:
                    badge = link.find(class_="badge")
                    if badge:
                        try:
                            orders["arrived"] = int(badge.get_text().strip())
                        except ValueError:
                            pass

        return orders

    def _parse_message_count_from_html(self, html: str) -> int:
        """Parse unread message count from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Look for unread badge in message section
        # Check for envelope icon with badge
        envelope_elem = soup.find(class_=re.compile(r"envelope", re.IGNORECASE))
        if envelope_elem:
            parent = envelope_elem.find_parent()
            if parent:
                badge = parent.find(class_="badge")
                if badge:
                    try:
                        return int(badge.get_text().strip())
                    except ValueError:
                        pass

        # Look for unread class
        unread_rows = soup.find_all(class_=re.compile(r"unread", re.IGNORECASE))
        if unread_rows:
            return len(unread_rows)

        return 0

    async def get_account_data(self) -> dict[str, Any]:
        """Get account information from the website."""
        await self._ensure_logged_in()

        # Get any page to extract the balance from header
        stock_url = self._get_url(STOCK_URL_TEMPLATE)
        html = await self._get_page(stock_url)

        balance = self._parse_balance_from_html(html)

        return {
            "username": self._username,
            "game": self._game,
            "game_name": self.game_name,
            "balance": balance,
        }

    async def get_stock_data(self) -> dict[str, Any]:
        """Get stock information from the website."""
        await self._ensure_logged_in()

        stock_url = self._get_url(STOCK_URL_TEMPLATE) + "/Offers"
        html = await self._get_page(stock_url)

        soup = BeautifulSoup(html, "html.parser")

        stock_data: dict[str, Any] = {
            "stock_count": 0,
            "stock_value": 0.0,
        }

        # Look for pagination info which often shows total count
        # Or count table rows
        page_text = soup.get_text()

        # Pattern: "1 to 25 from 156" or similar
        count_match = re.search(r"(?:from|of|von)\s*(\d+)", page_text, re.IGNORECASE)
        if count_match:
            stock_data["stock_count"] = int(count_match.group(1))

        # Alternative: Count rows in table
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            if rows:
                stock_data["stock_count"] = max(stock_data["stock_count"], len(rows) - 1)

        # Try to find total value
        value_match = re.search(r"(?:Total|Gesamt)[:\s]*(\d+[.,]\d{2})\s*€", page_text, re.IGNORECASE)
        if value_match:
            stock_data["stock_value"] = float(value_match.group(1).replace(",", "."))

        return stock_data

    async def get_seller_orders(self) -> dict[str, int]:
        """Get seller order counts from the website."""
        await self._ensure_logged_in()

        sales_url = self._get_url(SALES_URL_TEMPLATE)
        html = await self._get_page(sales_url)
        return self._parse_order_counts_from_html(html)

    async def get_buyer_orders(self) -> dict[str, int]:
        """Get buyer order counts from the website."""
        await self._ensure_logged_in()

        purchases_url = self._get_url(PURCHASES_URL_TEMPLATE)
        html = await self._get_page(purchases_url)
        return self._parse_order_counts_from_html(html)

    async def get_unread_messages(self) -> int:
        """Get unread message count from the website."""
        await self._ensure_logged_in()

        messages_url = self._get_url(MESSAGES_URL_TEMPLATE)
        html = await self._get_page(messages_url)
        return self._parse_message_count_from_html(html)

    async def test_connection(self) -> bool:
        """Test if we can connect and log in."""
        try:
            await self.login()
            return True
        except (CardmarketAuthError, CardmarketConnectionError):
            return False

    async def get_all_data(self) -> dict[str, Any]:
        """Get all available data from the website."""
        await self._ensure_logged_in()

        account_data = await self.get_account_data()
        stock_data = await self.get_stock_data()
        seller_orders = await self.get_seller_orders()
        buyer_orders = await self.get_buyer_orders()
        unread_messages = await self.get_unread_messages()

        return {
            "account": account_data,
            "stock_count": stock_data.get("stock_count", 0),
            "stock_value": stock_data.get("stock_value", 0.0),
            "seller_orders_paid": seller_orders.get("paid", 0),
            "seller_orders_sent": seller_orders.get("sent", 0),
            "seller_orders_arrived": seller_orders.get("arrived", 0),
            "buyer_orders_paid": buyer_orders.get("paid", 0),
            "buyer_orders_sent": buyer_orders.get("sent", 0),
            "buyer_orders_arrived": buyer_orders.get("arrived", 0),
            "unread_messages": unread_messages,
        }

    async def search_cards(self, search_term: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search for cards by name.
        
        Args:
            search_term: The card name to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of card dictionaries with name, set, url, and price info
        """
        encoded_search = urllib.parse.quote(search_term)
        search_url = self._get_url(SEARCH_URL_TEMPLATE)
        url = f"{search_url}?searchString={encoded_search}"
        
        html = await self._get_page(url)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        
        # Find all product rows
        product_rows = soup.find_all("div", id=re.compile(r"productRow\d+"))
        
        for row in product_rows[:max_results]:
            card_info = self._parse_search_result_row(row)
            if card_info:
                results.append(card_info)
        
        # If no product rows found, try finding product links directly
        if not results:
            # Match any game's product links
            product_links = soup.find_all("a", href=re.compile(rf"/en/{self._game}/Products/Singles/[^/]+/[^/]+$"))
            seen_urls = set()
            
            for link in product_links:
                href = link.get("href", "")
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                card_name = link.get_text(strip=True)
                if card_name and len(results) < max_results:
                    # Extract set name from URL
                    parts = href.split("/")
                    set_name = parts[-2] if len(parts) >= 2 else ""
                    
                    results.append({
                        "name": card_name,
                        "set": set_name.replace("-", " "),
                        "url": f"{BASE_URL}{href}",
                        "product_id": href,
                    })
        
        return results

    def _parse_search_result_row(self, row) -> dict[str, Any] | None:
        """Parse a search result row into card info."""
        # Find the product link - match any game's product links
        link = row.find("a", href=re.compile(rf"/en/{self._game}/Products/Singles/"))
        if not link:
            # Try generic pattern as fallback
            link = row.find("a", href=re.compile(r"/en/[^/]+/Products/Singles/"))
        if not link:
            return None
        
        href = link.get("href", "")
        card_name = link.get_text(strip=True)
        
        # Extract set name from URL
        parts = href.split("/")
        set_name = parts[-2] if len(parts) >= 2 else ""
        
        # Try to find price in the row
        price = None
        price_elem = row.find(class_="price-container")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r"(\d+[.,]\d{2})\s*€", price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", "."))
        
        return {
            "name": card_name,
            "set": set_name.replace("-", " "),
            "url": f"{BASE_URL}{href}",
            "product_id": href,
            "price_from": price,
        }

    async def get_card_prices(
        self, 
        card_url: str,
        language: str = "",
        condition: str = "",
        foil: str = "",
    ) -> dict[str, Any]:
        """Get detailed price information for a specific card.
        
        Args:
            card_url: The full URL or path to the card product page
            language: Language filter (1=English, 2=French, 3=German, etc.)
            condition: Condition filter (MT, NM, EX, GD, LP, PL, PO)
            foil: Foil filter (Y=Yes, N=No, empty=Any)
            
        Returns:
            Dictionary with price information
        """
        # Ensure we have a full URL
        if card_url.startswith("/"):
            card_url = f"{BASE_URL}{card_url}"
        elif not card_url.startswith("http"):
            card_url = f"{BASE_URL}/{card_url}"
        
        # Build filter URL for the offers page
        # Cardmarket uses query parameters like: ?language=1&minCondition=NM&isFoil=Y
        filter_params = []
        if language:
            filter_params.append(f"language={language}")
        if condition:
            filter_params.append(f"minCondition={condition}")
        if foil:
            filter_params.append(f"isFoil={foil}")
        
        filter_url = card_url
        if filter_params:
            separator = "&" if "?" in card_url else "?"
            filter_url = f"{card_url}{separator}{'&'.join(filter_params)}"
        
        html = await self._get_page(filter_url)
        soup = BeautifulSoup(html, "html.parser")
        
        prices: dict[str, Any] = {
            "name": "",
            "set": "",
            "url": card_url,
            "filter_url": filter_url if filter_params else None,
            "price_from": None,
            "price_trend": None,
            "price_30_day_avg": None,
            "price_7_day_avg": None,
            "price_1_day_avg": None,
            "available_items": 0,
        }
        
        # Get card name from h1
        h1 = soup.find("h1")
        if h1:
            title_text = h1.get_text(strip=True)
            # Title format is usually "Card NameSet Name - Singles"
            prices["name"] = title_text.split(" - ")[0] if " - " in title_text else title_text
        
        # Find the info list container with price data
        info_list = soup.find(class_="info-list-container")
        if info_list:
            # Get all dt (labels) and dd (values) pairs
            dts = info_list.find_all("dt")
            dds = info_list.find_all("dd")
            
            for i, dt in enumerate(dts):
                if i >= len(dds):
                    break
                    
                label = dt.get_text(strip=True).lower()
                value_elem = dds[i]
                value_text = value_elem.get_text(strip=True)
                
                # Parse different price types
                if "from" in label or "ab" in label:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", value_text)
                    if price_match:
                        prices["price_from"] = float(price_match.group(1).replace(",", "."))
                
                elif "trend" in label:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", value_text)
                    if price_match:
                        prices["price_trend"] = float(price_match.group(1).replace(",", "."))
                
                elif "30-day" in label or "30 day" in label:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", value_text)
                    if price_match:
                        prices["price_30_day_avg"] = float(price_match.group(1).replace(",", "."))
                
                elif "7-day" in label or "7 day" in label:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", value_text)
                    if price_match:
                        prices["price_7_day_avg"] = float(price_match.group(1).replace(",", "."))
                
                elif "1-day" in label or "1 day" in label:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", value_text)
                    if price_match:
                        prices["price_1_day_avg"] = float(price_match.group(1).replace(",", "."))
                
                elif "available" in label or "verfügbar" in label:
                    count_match = re.search(r"(\d+)", value_text)
                    if count_match:
                        prices["available_items"] = int(count_match.group(1))
                
                elif "printed" in label or "gedruckt" in label:
                    prices["set"] = value_text
        
        # Alternative: Parse from definition lists if info-list not found
        if prices["price_from"] is None:
            dds = soup.find_all("dd")
            for i, dd in enumerate(dds):
                text = dd.get_text(strip=True)
                if '€' in text:
                    price_match = re.search(r"(\d+[.,]\d{2})\s*€", text)
                    if price_match:
                        price = float(price_match.group(1).replace(",", "."))
                        if prices["price_from"] is None:
                            prices["price_from"] = price
                        elif prices["price_trend"] is None:
                            prices["price_trend"] = price
                        elif prices["price_30_day_avg"] is None:
                            prices["price_30_day_avg"] = price
        
        return prices

    async def get_tracked_card_prices(
        self, 
        tracked_cards: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Get prices for multiple tracked cards with their filters.
        
        Args:
            tracked_cards: List of tracked card dictionaries with url and filter info
            
        Returns:
            Dictionary mapping card unique keys to their price data
        """
        await self._ensure_logged_in()
        
        results = {}
        for card in tracked_cards:
            url = card.get("url", "")
            unique_key = card.get("unique_key", url)
            language = card.get("language", "")
            condition = card.get("condition", "")
            foil = card.get("foil", "")
            
            try:
                prices = await self.get_card_prices(
                    url, 
                    language=language,
                    condition=condition,
                    foil=foil,
                )
                # Add filter info to the result
                prices["language"] = language
                prices["condition"] = condition
                prices["foil"] = foil
                results[unique_key] = prices
            except Exception as err:
                _LOGGER.warning("Failed to get prices for %s: %s", unique_key, err)
                results[unique_key] = {"error": str(err)}
        
        return results
