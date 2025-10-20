import telebot
import sqlite3
import datetime
import logging
import os
from telebot import types

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения (ВАЖНО для Render)
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8369809235:AAF5gKSyPMkAgyCb3a08gfjPye0dz0-zKOU')

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения временных данных пользователей
user_data = {}

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                application_text TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")

# Сохранение заявки в БД
def save_application(user_id, username, full_name, phone, application_text):
    try:
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO applications (user_id, username, full_name, phone, application_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, phone, application_text))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving application: {e}")
        return False

# Главное меню
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('📝 Оставить заявку')
    btn2 = types.KeyboardButton('ℹ️ О нас')
    btn3 = types.KeyboardButton('📞 Контакты')
    markup.add(btn1, btn2, btn3)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    welcome_text = f"""
Привет, {user.first_name}! 👋

Я бот для приема заявок. 
Я помогу вам оставить заявку, и наш специалист свяжется с вами в ближайшее время.

Для начала работы нажмите кнопку «📝 Оставить заявку» или используйте команду /application
    """
    main_menu(message.chat.id)
    bot.send_message(message.chat.id, welcome_text)

# Обработчик команды /application
@bot.message_handler(commands=['application'])
def start_application(message):
    user_id = message.from_user.id
    user_data[user_id] = {'step': 1}
    
    # Убираем клавиатуру для ввода имени
    remove_markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Отлично! Давайте оформим заявку.\n\nКак к вам обращаться? (Введите ваше ФИО):", 
                     reply_markup=remove_markup)

# Обработчик кнопки "Оставить заявку"
@bot.message_handler(func=lambda message: message.text == '📝 Оставить заявку')
def handle_application_button(message):
    start_application(message)

# Обработчик кнопки "О нас"
@bot.message_handler(func=lambda message: message.text == 'ℹ️ О нас')
def handle_about(message):
    about_text = """
🤖 О нашем боте:

Мы предоставляем качественные услуги через удобную систему заявок. 
Оставьте заявку, и наш специалист свяжется с вами для уточнения деталей.

📋 Что мы предлагаем:
• Консультации
• Техническую поддержку пользователей

Работаем быстро и качественно!
    """
    bot.send_message(message.chat.id, about_text)

# Обработчик кнопки "Контакты"
@bot.message_handler(func=lambda message: message.text == '📞 Контакты')
def handle_contacts(message):
    contacts_text = """
📞 Наши контакты:

Телефон: +7 (918) 965-79-93
Email: -
Адрес: г. Санкт-Петербург

⏰ Время работы:
Пн-Пт: 8:30 - 16:30
Сб-Вс: выходной
    """
    bot.send_message(message.chat.id, contacts_text)

# Обработчик текстовых сообщений (для многошаговой формы)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user = message.from_user
    
    # Если пользователь в процессе заполнения заявки
    if user_id in user_data:
        current_step = user_data[user_id].get('step', 0)
        
        if current_step == 1:
            # Сохраняем ФИО
            user_data[user_id]['full_name'] = message.text
            user_data[user_id]['step'] = 2
            
            # Запрашиваем телефон
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_phone = types.KeyboardButton('📱 Отправить номер телефона', request_contact=True)
            markup.add(btn_phone)
            bot.send_message(message.chat.id, "Теперь укажите ваш номер телефона:", reply_markup=markup)
            
        elif current_step == 2:
            # Сохраняем телефон (если введен вручную)
            user_data[user_id]['phone'] = message.text
            user_data[user_id]['step'] = 3
            bot.send_message(message.chat.id, "Теперь опишите, чем мы можем вам помочь:")
            
        elif current_step == 3:
            # Сохраняем текст заявки и завершаем
            user_data[user_id]['application_text'] = message.text
            
            # Сохраняем в БД
            success = save_application(
                user_id,
                user.username,
                user_data[user_id]['full_name'],
                user_data[user_id].get('phone', 'Не указан'),
                user_data[user_id]['application_text']
            )
            
            if success:
                # Отправляем подтверждение пользователю
                confirmation_text = f"""
✅ Ваша заявка принята!

📋 Данные заявки:
• ФИО: {user_data[user_id]['full_name']}
• Телефон: {user_data[user_id].get('phone', 'Не указан')}
• Описание: {user_data[user_id]['application_text']}

Наш специалист свяжется с вами в ближайшее время.
                """
                bot.send_message(message.chat.id, confirmation_text)
                
                # Уведомление администратору
                admin_chat_id = os.environ.get('ADMIN_CHAT_ID', '1060377514')
                admin_text = f"""
🚨 НОВАЯ ЗАЯВКА!

👤 Клиент: {user_data[user_id]['full_name']}
📞 Телефон: {user_data[user_id].get('phone', 'Не указан')}
📝 Описание: {user_data[user_id]['application_text']}
👤 Username: @{user.username if user.username else 'Не указан'}
🆔 User ID: {user_id}
⏰ Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                try:
                    bot.send_message(admin_chat_id, admin_text)
                except Exception as e:
                    logger.warning(f"Admin notification failed: {e}")
                
            else:
                bot.send_message(message.chat.id, "❌ Произошла ошибка при сохранении заявки. Пожалуйста, попробуйте позже.")
            
            # Очищаем данные пользователя
            del user_data[user_id]
            
            # Возвращаем главное меню
            main_menu(message.chat.id)
    
    else:
        # Если сообщение не связано с заявкой, показываем меню
        main_menu(message.chat.id)

# Обработчик контактов
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    if user_id in user_data and user_data[user_id].get('step') == 2:
        phone_number = message.contact.phone_number
        user_data[user_id]['phone'] = phone_number
        user_data[user_id]['step'] = 3
        
        # Убираем клавиатуру с кнопкой телефона
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Спасибо! Теперь опишите, чем мы можем вам помочь:", 
                         reply_markup=remove_markup)

# Обработчик неизвестных команд
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.reply_to(message, "Я вас не понял. Используйте кнопки меню или команду /start")

# Проверка работы бота
def check_bot():
    try:
        bot_info = bot.get_me()
        logger.info(f"Бот @{bot_info.username} запущен и работает!")
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке бота: {e}")
        return False

# Запуск бота
if __name__ == '__main__':
    print("Запуск бота для заявок...")
    init_db()
    
    if check_bot():
        logger.info("Бот готов к работе. Запускаем опрос...")
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Ошибка при работе бота: {e}")
    else:
        logger.error("Не удалось запустить бота")

