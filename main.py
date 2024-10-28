import requests
import csv
import json
import time
import logging
import smtplib
from logging.handlers import RotatingFileHandler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Конфигурации
GOPHISH_API_KEY = 'ce77a2ee2424678030042cc563d41b87ba2819fbe283b5089f94c9e43b974ada'
GOPHISH_URL = 'https://gophish_server_address/api/campaigns/?api_key=' + GOPHISH_API_KEY
CHECK_INTERVAL = 3600  # интервал в секундах
ERROR_EMAILS = ['kurokim@yandex.ru']  # список email для отправки уведомлений
LOG_FILE = 'gophish_script.log'
CAMPAIGN_STATUS_FILE = 'campaign_status.json'
TIMELINE_CSV_FOLDER = './timelines/'

# Настройка логирования с ротацией
logger = logging.getLogger('GophishLogger')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=100 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# Функция отправки e-mail уведомлений
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = 'kurokimala@gmail.com'
        msg['To'] = ", ".join(ERROR_EMAILS)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.yourdomain.com', 587) as server:
            server.starttls()
            server.login('your_email', 'your_password')
            server.sendmail(msg['From'], ERROR_EMAILS, msg.as_string())
    except Exception as e:
        logger.error("Ошибка при отправке e-mail: %s", e)


# Функция для получения данных кампаний из GoPhish
def fetch_campaigns():
    try:
        response = requests.get(GOPHISH_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error("Ошибка при получении данных: %s", e)
        send_email("Ошибка при выгрузке данных из GoPhish", str(e))
        return []


# Загрузка существующих данных из файла
def load_existing_data():
    try:
        with open(CAMPAIGN_STATUS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


# Сохранение обновленных данных
def save_data(data):
    with open(CAMPAIGN_STATUS_FILE, 'w') as file:
        json.dump(data, file, indent=4)


# Проверка и обновление статусов кампаний
def update_campaign_statuses():
    existing_data = load_existing_data()
    new_data = fetch_campaigns()
    for campaign in new_data:
        campaign_id = campaign['id']
        if campaign_id not in existing_data or existing_data[campaign_id]['status'] != campaign['status']:
            existing_data[campaign_id] = {'name': campaign['name'], 'status': campaign['status']}
            update_campaign_timeline(campaign_id)
    save_data(existing_data)


# Обновление timeline для кампании
def update_campaign_timeline(campaign_id):
    url = f"https://gophish_server_address/api/campaigns/{campaign_id}/timeline/?api_key={GOPHISH_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        timeline_data = response.json()
        csv_filename = f"{TIMELINE_CSV_FOLDER}/campaign_{campaign_id}_timeline.csv"
        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for entry in timeline_data:
                writer.writerow([entry['email'], entry['event'], entry['time']])
        logger.info("Обновлен timeline для кампании %s", campaign_id)
    else:
        logger.error("Ошибка при получении timeline для кампании %s", campaign_id)
        send_email("Ошибка при получении timeline", f"Кампания ID: {campaign_id}")


# Основной цикл
def main():
    while True:
        try:
            update_campaign_statuses()
            logger.info("Данные обновлены.")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error("Необработанная ошибка: %s", e)
            send_email("Необработанная ошибка в скрипте GoPhish", str(e))


if __name__ == "__main__":
    main()
