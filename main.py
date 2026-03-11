import schedule
import time
from dispatcher import run_daily_task, run_payments_statistics_task_for_day

schedule.every().day.at("00:01").do(run_daily_task)
schedule.every().day.at("05:00").do(run_payments_statistics_task_for_day)

while True:
    schedule.run_pending()
    time.sleep(60)