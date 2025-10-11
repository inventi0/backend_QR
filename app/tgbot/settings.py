import os
from pydantic import BaseModel, Field

class BotSettings(BaseModel):
    token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    mode: str = Field(default_factory=lambda: os.getenv("BOT_MODE", "polling"))  # polling|webhook
    webhook_base_url: str = Field(default_factory=lambda: os.getenv("WEBHOOK_BASE_URL", ""))
    webhook_path: str = Field(default="/tg/webhook")
    webhook_secret_token: str | None = Field(default_factory=lambda: os.getenv("WEBHOOK_SECRET_TOKEN"))

    # бизнес-настройки
    admin_ids: set[int] = Field(
        default_factory=lambda: {
            int(x.strip()) for x in os.getenv("ADMIN_TELEGRAM_ID", "")
            .replace("[","").replace("]","").split(",") if x.strip().isdigit()
        }
    )
    bot_username: str = Field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))
    debug_mode: bool = Field(default_factory=lambda: os.getenv("DEBUG_MODE", "0").lower() in ("1","true","yes"))

    # YooKassa
    yk_shop_id: str | None = Field(default_factory=lambda: os.getenv("YK_SHOP_ID"))
    yk_secret_key: str | None = Field(default_factory=lambda: os.getenv("YK_SECRET_KEY"))
    pay_return_url: str = Field(default_factory=lambda: os.getenv("PAY_RETURN_URL", "https://example.com/thanks"))

    # Реквизиты/подпись
    merchant_name: str = Field(default_factory=lambda: os.getenv("MERCHANT_NAME", "MyShop"))
    merchant_acc: str = Field(default_factory=lambda: os.getenv("MERCHANT_IBAN_OR_ACC", ""))
    default_currency: str = Field(default_factory=lambda: os.getenv("DEFAULT_CURRENCY", "RUB"))
    start_secret: str = Field(default_factory=lambda: os.getenv("START_SECRET", ""))
