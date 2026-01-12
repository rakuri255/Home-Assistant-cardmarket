# Cardmarket Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant integration for Cardmarket. Monitor your Cardmarket account, orders, and card prices directly in Home Assistant.

## Features

- **Account Balance**: Current account balance
- **Seller Orders**: Number of sent and arrived orders as seller
- **Buyer Orders**: Number of sent and arrived orders as buyer
- **Unread Messages**: Number of unread messages
- **Card Tracking**: Monitor prices of individual cards
- **Multi-Game Support**: Supports all Cardmarket games

## Supported Games

- Magic: The Gathering
- Pokémon
- Yu-Gi-Oh!
- One Piece
- Lorcana
- Flesh and Blood
- Star Wars Unlimited
- Digimon
- Dragon Ball Super
- Vanguard
- Weiß Schwarz
- Final Fantasy
- Force of Will

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

### Adding the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Cardmarket"
4. Enter your login credentials:
   - Username
   - Password
   - Game (e.g. Magic, Pokémon, Yu-Gi-Oh!)
5. Click "Submit"

**Note**: You can set up multiple instances for different games.

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.cardmarket_account_balance` | Account balance in Euro |
| `sensor.cardmarket_seller_orders_sent` | Sent seller orders |
| `sensor.cardmarket_seller_orders_arrived` | Arrived seller orders |
| `sensor.cardmarket_buyer_orders_sent` | Sent buyer orders |
| `sensor.cardmarket_buyer_orders_arrived` | Arrived buyer orders |
| `sensor.cardmarket_unread_messages` | Unread messages |

## Card Tracking

You can track individual cards and monitor their prices.

### Services

#### `cardmarket.search_card`
Search for a card and return results.

```yaml
service: cardmarket.search_card
data:
  query: "Lightning Bolt"
```

## Automations

### Example: Notification for New Order

```yaml
automation:
  - alias: "Cardmarket - New Order"
    trigger:
      - platform: state
        entity_id: sensor.cardmarket_seller_orders_sent
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Cardmarket"
          message: "You have a new order!"
```

### Example: Price Alert

```yaml
automation:
  - alias: "Cardmarket - Price Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.cardmarket_card_lightning_bolt
        below: 0.10
    action:
      - service: notify.mobile_app
        data:
          title: "Cardmarket Price Alert"
          message: "Lightning Bolt is below 0.10€!"
```

## Update Interval

The integration updates data every 60 minutes by default to avoid overloading the Cardmarket website. You can configure the update interval during setup:

- **Minimum**: 5 minutes
- **Maximum**: 24 hours (1440 minutes)
- **Default**: 60 minutes

A higher interval is recommended to be respectful of Cardmarket's servers.

## Options

After setup, you can configure additional settings under **Options**:
- Add cards for price monitoring

## Troubleshooting

### "Invalid credentials"

- Check your username and password
- Make sure your account is not locked

### "Connection failed"

- Check your internet connection
- Cardmarket servers may be temporarily unavailable
- Try again later

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## Support

If you encounter any problems, please create an issue on GitHub.
