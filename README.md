# Babka Bot - AI-powered Video and Photo Generation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Telegram Bot Token
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/babka-bot.git
cd babka-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual values
```

4. Run database migrations:
```bash
python RUN_MIGRATIONS.py
```

5. Start the bot:
```bash
python main.py
```

## 🏗️ Architecture

The bot uses a modular architecture with the following structure:

```
app/
├── billing/          # Coins, plans, payments
│   ├── config.py     # All prices and plans
│   ├── coins.py      # Atomic coin operations
│   ├── plans.py      # Subscription management
│   └── payments.py    # Payment processing
├── db/               # Database layer
│   ├── models.sql    # Database schema
│   └── queries.py    # Database operations
├── handlers/         # Telegram handlers
├── ui/               # Keyboards and messages
├── jobs/             # Job management
└── utils/            # Utilities
    ├── env.py        # Environment config
    ├── logging.py    # Logging setup
    └── cron.py       # Background tasks
```

## 💰 Billing System

The bot uses a coin-based billing system:

- **Video generation**: 10 coins
- **Photo (basic)**: 1 coin
- **Photo (premium)**: 2 coins
- **Virtual try-on**: 1 coin

### Plans
- **Lite**: 1,990 ₽ → 120 coins
- **Standard**: 2,490 ₽ → 210 coins (recommended)
- **Pro**: 4,990 ₽ → 440 coins

### Features
- ✅ Atomic coin operations
- ✅ Automatic subscription expiry handling
- ✅ Idempotent payment processing
- ✅ Transaction logging
- ✅ Welcome bonuses (one-time)

## 🧪 Testing

Run tests:
```bash
pytest tests/ -v
```

Test coverage includes:
- Coin operations (spend, add, balance)
- Plan activation and expiry
- Payment processing
- Transaction logging

## 🚀 Deployment

### Railway
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Manual Deployment
1. Set up PostgreSQL database
2. Configure environment variables
3. Run migrations: `python RUN_MIGRATIONS.py`
4. Start the bot: `python main.py`

## 📊 Database Schema

### Users Table
- `user_id` (BIGINT PRIMARY KEY)
- `coins` (INT DEFAULT 0)
- `plan` (VARCHAR(20) DEFAULT 'lite')
- `plan_expiry` (TIMESTAMP NULL)
- `admin_coins` (INT DEFAULT 0)
- `created_at` (TIMESTAMP DEFAULT NOW())
- `updated_at` (TIMESTAMP DEFAULT NOW())

### Transactions Table
- `id` (BIGSERIAL PRIMARY KEY)
- `user_id` (BIGINT REFERENCES users)
- `operation_type` (TEXT)
- `coins_spent` (INT)
- `status` (TEXT DEFAULT 'pending')
- `created_at` (TIMESTAMP DEFAULT NOW())

### Payments Table
- `id` (UUID PRIMARY KEY)
- `user_id` (BIGINT REFERENCES users)
- `subscription_type` (TEXT)
- `amount` (NUMERIC(12,2))
- `status` (TEXT)
- `created_at` (TIMESTAMP DEFAULT NOW())
- `idempotent_key` (TEXT UNIQUE)

## 🔧 Configuration

All prices and plans are centralized in `app/billing/config.py`:

```python
# Operation costs
COST_VIDEO = 10
COST_TRANSFORM = 1
COST_TRANSFORM_PREMIUM = 2
COST_TRYON = 1

# Plans
PLANS = {
    "lite": {"price_rub": 1990, "coins": 120},
    "standard": {"price_rub": 2490, "coins": 210},
    "pro": {"price_rub": 4990, "coins": 440},
}
```

## 🛠️ Development

### Adding New Features
1. Create handlers in `app/handlers/`
2. Add UI components in `app/ui/`
3. Update billing logic in `app/billing/`
4. Add tests in `tests/`

### Database Changes
1. Update `app/db/models.sql`
2. Create migration in `FINAL_MIGRATION.sql`
3. Test with `python RUN_MIGRATIONS.py`

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support, contact: antonkudo.ai@gmail.com