import os
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
import logging
from datetime import datetime

# --- Укажите нужную директорию ---
PROJECT_ROOT = r"C:\Users\PC\PycharmProjects\backend_QR" #нужно указать свою либо рефаторинг сделать!!!
qr_folder = os.path.join(PROJECT_ROOT, "qr_codes")
log_dir = os.path.join(PROJECT_ROOT, "logs")

# --- Настройка логирования ---
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"qr_generator_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --- Создание папки для QR-кодов ---
if not os.path.exists(qr_folder):
    try:
        os.makedirs(qr_folder)
        logger.info(f"Создана папка: {qr_folder}")
    except Exception as e:
        logger.error(f"Не удалось создать папку {qr_folder}: {e}")
        exit(1)

def generate_unique_qr_with_text(output_folder=qr_folder):
    try:
        # --- Генерация уникального ID ---
        unique_id = str(uuid.uuid4())
        logger.info(f"Сгенерирован уникальный ID: {unique_id}")

        # --- Создание QR-кода ---
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(unique_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        logger.info("QR-код успешно создан")

        # --- Преобразование в RGB для добавления текста ---
        img = img.convert("RGB")

        # --- Настройка шрифта ---
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            logger.info("Используется шрифт arial.ttf")
        except Exception as e:
            font = ImageFont.load_default()
            logger.warning("Шрифт arial.ttf не найден, используется стандартный шрифт")

        draw = ImageDraw.Draw(img)

        # --- Размеры текста ---
        text_width = font.getlength(unique_id)
        text_height = font.getbbox("A")[3] - font.getbbox("A")[1]

        width, height = img.size
        x = (width - text_width) / 2
        y = height - text_height - 10

        # --- Рисуем текст под QR-кодом ---
        draw.text((x, y), unique_id, fill="black", font=font)
        logger.info("Текст успешно добавлен к QR-коду")

        # --- Сохранение файла ---
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"qr_{timestamp}_{unique_id[:8]}.png"
        output_path = os.path.join(output_folder, filename)

        img.save(output_path)
        logger.info(f"QR-код сохранён: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}", exc_info=True)
        return None

# === Точка входа ===
if __name__ == "__main__":
    logger.info("Запуск генератора QR-кодов")
    result = generate_unique_qr_with_text()
    if result:
        logger.info("Генерация QR-кода завершена успешно")
    else:
        logger.error("Генерация QR-кода завершена с ошибкой")