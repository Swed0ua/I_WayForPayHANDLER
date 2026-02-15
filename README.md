# WayForPay → Bitrix24 Handler

Сервіс щоденно о 05:00 збирає статистику платежів WayForPay за попередній день, експортує в Excel і створює угоду з товарами в Bitrix24.

## Швидкий старт

### 1. Встановлення

```bash
git clone <repository-url>
cd I_WEYFORPAY_HANDLER
python -m venv venv
source venv/bin/activate   # Linux/Mac
# або
venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

### 2. Налаштування

Створіть `.env`:

```
WAYFORPAY_MERCHANT_ACCOUNT=...
WAYFORPAY_MERCHANT_SECRET_KEY=...
BITRIX24_WEBHOOK_URL=...
```

### 3. Запуск

```bash
python main.py
```
---

## Структура проєкту

| Модуль | Опис |
|--------|------|
| `main.py` | Планувальник: щодня о 05:00 запускає задачу |
| `dispatcher.py` | Оркестрація: WayForPay → Excel → угода в B24 |
| `config.py` | ID категорії та стадії угод Bitrix24 |
| `utils.py` | Робота з датами та timestamp |
| `services/B24/` | Bitrix24: адаптер полів, сервіс API, конфіг каталогу |
| `services/WayForPay/` | WayForPay: отримання платежів, адаптер, конфіг |
| `services/ExcelExport/` | Експорт статистики в Excel |

---

## Systemd Service

### 1. Файл сервісу

```bash
sudo nano /etc/systemd/system/I_WEYFORPAY_HANDLER.service
```

### 2. Вміст (підстав свій шлях до проєкту)

```ini
[Unit]
Description=WayForPay to Bitrix24 daily statistics handler
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/I_WEYFORPAY_HANDLER
Environment=PATH=/path/to/I_WEYFORPAY_HANDLER/venv/bin
Environment=PYTHONPATH=/path/to/I_WEYFORPAY_HANDLER
ExecStart=/path/to/I_WEYFORPAY_HANDLER/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=I_WEYFORPAY_HANDLER

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/path/to/I_WEYFORPAY_HANDLER

[Install]
WantedBy=multi-user.target
```

### 3. Увімкнення та запуск

```bash
sudo systemctl daemon-reload
sudo systemctl enable I_WEYFORPAY_HANDLER
sudo systemctl start I_WEYFORPAY_HANDLER
sudo systemctl status I_WEYFORPAY_HANDLER
```

---

## Керування сервісом

| Дія | Команда |
|-----|--------|
| Запуск | `sudo systemctl start I_WEYFORPAY_HANDLER` |
| Зупинка | `sudo systemctl stop I_WEYFORPAY_HANDLER` |
| Перезапуск | `sudo systemctl restart I_WEYFORPAY_HANDLER` |
| Статус | `sudo systemctl status I_WEYFORPAY_HANDLER` |
| Логи (онлайн) | `sudo journalctl -u I_WEYFORPAY_HANDLER -f` |
| Останні 50 рядків | `sudo journalctl -u I_WEYFORPAY_HANDLER -n 50` |
| Всі логи | `sudo journalctl -u I_WEYFORPAY_HANDLER` |

---

## Перевірка

- Процес: `ps aux | grep "python main.py"`
- Сервіс у списку: `sudo systemctl list-units --type=service | grep I_WEYFORPAY`
