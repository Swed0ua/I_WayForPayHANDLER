import schedule
import time
from dispatcher import run_payments_statistics_task_for_day

schedule.every().day.at("05:00").do(run_payments_statistics_task_for_day)

while True:
    schedule.run_pending()
    time.sleep(60)