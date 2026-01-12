# Cardmarket Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant integration for the Cardmarket API. This integration allows you to monitor your Cardmarket account data, orders, and stock directly in Home Assistant.

## Features

- **Account Balance**: Shows your current account balance
- **Unpaid Amount**: Shows outstanding amounts
- **Stock Articles**: Number of articles in your stock
- **Stock Value**: Total value of your stock
- **Seller Orders**: Number of paid and sent orders as a seller
- **Buyer Orders**: Number of paid and sent orders as a buyer
- **Unread Messages**: Number of unread messages

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click on the three dots in the top right corner and select "Custom repositories"
4. Add the repository URL: `https://github.com/rakuri255/Home-Assistant-Cardmarket`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Cardmarket" and install it
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/cardmarket` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

### Getting API Access

1. Log in to [Cardmarket](https://www.cardmarket.com)
2. Go to your profile
3. Create a new "Dedicated App" under the API settings
4. Note down the following values:
   - App Token
   - App Secret
   - Access Token
   - Access Token Secret

**Note**: The Cardmarket API is only available for professional sellers and is subject to a manual approval process.

### Adding the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Cardmarket"
4. Enter your API credentials:
   - App Token
   - App Secret
   - Access Token
   - Access Token Secret
5. Click "Submit"

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.cardmarket_account_balance` | Account balance in Euro |
| `sensor.cardmarket_unpaid_amount` | Unpaid amount |
| `sensor.cardmarket_provider_amount` | Provider recharge amount |
| `sensor.cardmarket_stock_count` | Number of stock articles |
| `sensor.cardmarket_stock_value` | Total stock value |
| `sensor.cardmarket_seller_orders_paid` | Paid seller orders |
| `sensor.cardmarket_seller_orders_sent` | Sent seller orders |
| `sensor.cardmarket_buyer_orders_paid` | Paid buyer orders |
| `sensor.cardmarket_buyer_orders_sent` | Sent buyer orders |
| `sensor.cardmarket_unread_messages` | Unread messages |

## Automations

### Example: Notification for New Paid Order

```yaml
automation:
  - alias: "Cardmarket - New Paid Order"
    trigger:
      - platform: state
        entity_id: sensor.cardmarket_seller_orders_paid
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Cardmarket"
          message: "You have a new paid order!"
```

### Example: Notification for Unread Message

```yaml
automation:
  - alias: "Cardmarket - Unread Message"
    trigger:
      - platform: numeric_state
        entity_id: sensor.cardmarket_unread_messages
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Cardmarket"
          message: "You have {{ states('sensor.cardmarket_unread_messages') }} unread message(s)!"
```

## Update Interval

The integration updates data every 5 minutes. This is a good balance between freshness and API usage.

## Troubleshooting

### "Invalid authentication credentials"

- Check that all four API tokens are entered correctly
- Make sure your API app is still active
- Verify that your API access has not been revoked

### "Failed to connect to Cardmarket API"

- Check your internet connection
- Cardmarket servers may be temporarily unavailable
- Try again later

## API Usage Notes

According to Cardmarket documentation:
- Dedicated Apps are only intended to support normal Cardmarket activities
- Excessive use of Marketplace resources (products, articles, prices) may lead to blocking
- This integration focuses on account management and order tracking

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## Support

If you encounter any problems, please create an issue on GitHub.
