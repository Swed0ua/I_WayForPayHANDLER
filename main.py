import schedule
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from dispatcher import run_daily_task, run_payments_statistics_task_for_day, run_payments_statistics_task_from_gmail_csv

# schedule.every().day.at("00:01").do(run_daily_task)
_KYIV_TZ = ZoneInfo("Europe/Kyiv")
_last_run_date = None


def run_gmail_stats_at_11_kyiv() -> None:
    global _last_run_date
    now_kyiv = datetime.now(_KYIV_TZ)
    if now_kyiv.hour == 11 and now_kyiv.minute == 0 and _last_run_date != now_kyiv.date():
        run_payments_statistics_task_from_gmail_csv(days_ago=0)
        _last_run_date = now_kyiv.date()


schedule.every(1).minutes.do(run_gmail_stats_at_11_kyiv)

while True:
    schedule.run_pending()
    time.sleep(60)