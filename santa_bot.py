import telebot
import json
import random
import os
from telebot import types
from telebot import apihelper

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================

# Вставьте ваш токен от BotFather
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# НАСТРОЙКА ПРОКСИ (если он нужен)
# Раскомментируйте 2 строки ниже и вставьте рабочий прокси БЕЗ логина и пароля.
# Если прокси не нужен (или у вас VPN) - оставьте эти строки закомментированными.
# apihelper.proxy = {'https': 'socks5://IP_АДРЕС:ПОРТ'} 
# Пример: apihelper.proxy = {'https': 'socks5://188.215.44.164:1080'}

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Файл для сохранения базы данных пользователей и игр
DB_FILE = 'santa_data.json'

# ==========================================
# 2. РАБОТА С БАЗОЙ ДАННЫХ
# ==========================================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "games": {}}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "games": {}}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 3. КОМАНДЫ БОТА
# ==========================================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('🎅 Создать игру')
    btn2 = types.KeyboardButton('👤 Присоединиться')
    btn3 = types.KeyboardButton('📋 Мои игры')
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}!\n\n"
        "Я бот для игры в Тайного Санту. Выбери действие на клавиатуре:\n"
        "1. Создай игру и получи код.\n"
        "2. Отправь код друзьям, чтобы они присоединились.\n"
        "3. Когда все соберутся, запусти жеребьевку.", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '🎅 Создать игру')
def create_game(message):
    db = load_db()
    user_id = str(message.from_user.id)
    
    game_id = str(random.randint(1000, 9999))
    
    db["games"][game_id] = {
        "creator": user_id,
        "participants": [user_id],
        "results": {}
    }
    
    if "users" not in db:
        db["users"] = {}
    db["users"][user_id] = message.from_user.first_name
    
    save_db(db)
    
    bot.send_message(
        message.chat.id, 
        f"Игра создана! 🎉\n"
        f"Код вашей игры: **{game_id}**\n\n"
        f"Отправьте этот код друзьям. Они должны нажать «👤 Присоединиться» и ввести его.\n"
        f"Вы автоматически добавлены в игру.\n\n"
        f"Когда все соберутся, напишите /draw {game_id} для жеребьевки.",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == '👤 Присоединиться')
def join_game_start(message):
    msg = bot.send_message(message.chat.id, "Введите код игры (4 цифры):")
    bot.register_next_step_handler(msg, process_join)

def process_join(message):
    game_id = message.text.strip()
    db = load_db()
    user_id = str(message.from_user.id)
    
    if game_id not in db["games"]:
        bot.send_message(message.chat.id, "❌ Игра с таким кодом не найдена. Попробуйте еще раз.")
        return
        
    if user_id in db["games"][game_id]["participants"]:
        bot.send_message(message.chat.id, "Вы уже участвуете в этой игре!")
        return
        
    db["games"][game_id]["participants"].append(user_id)
    db["users"][user_id] = message.from_user.first_name
    save_db(db)
    
    count = len(db["games"][game_id]["participants"])
    bot.send_message(message.chat.id, f"✅ Вы присоединились к игре {game_id}!\nСейчас участников: {count}.")

@bot.message_handler(func=lambda message: message.text == '📋 Мои игры')
def my_games(message):
    db = load_db()
    user_id = str(message.from_user.id)
    my_games_list = []
    
    for gid, game in db["games"].items():
        if user_id in game["participants"]:
            status = "результаты готовы ✅" if game["results"] else "ожидание жеребьевки ⏳"
            my_games_list.append(f"Игра {gid} — {status}")
            
    if not my_games_list:
        bot.send_message(message.chat.id, "Вы пока не участвуете ни в одной игре.")
    else:
        bot.send_message(message.chat.id, "Ваши игры:\n" + "\n".join(my_games_list))

@bot.message_handler(commands=['draw'])
def draw_santa(message):
    try:
        game_id = message.text.split()[1]
    except IndexError:
        bot.send_message(message.chat.id, "Напишите код игры после команды. Пример: /draw 1234")
        return
        
    db = load_db()
    user_id = str(message.from_user.id)
    
    if game_id not in db["games"]:
        bot.send_message(message.chat.id, "Игра не найдена.")
        return
        
    game = db["games"][game_id]
    
    if game["creator"] != user_id:
        bot.send_message(message.chat.id, "Только создатель игры может запускать жеребьевку!")
        return
        
    if game["results"]:
        bot.send_message(message.chat.id, "В этой игре уже была проведена жеребьевка!")
        return
        
    participants = game["participants"]
    
    if len(participants) < 3:
        bot.send_message(message.chat.id, f"Для игры нужно минимум 3 человека. Сейчас: {len(participants)}.")
        return
        
    # Алгоритм перемешивания (каждый дарит другому, не себе)
    shuffled = participants[:]
    while True:
        random.shuffle(shuffled)
        # Проверка, что никто не дарит сам себе
        if all(participants[i] != shuffled[i] for i in range(len(participants))):
            break
            
    # Сохраняем результаты
    for i in range(len(participants)):
        giver = participants[i]
        receiver = shuffled[i]
        game["results"][giver] = receiver
        
    save_db(db)
    
    # Рассылка результатов
    bot.send_message(message.chat.id, f"🎲 Жеребьевка в игре {game_id} завершена! Каждый участник получил имя в личные сообщения.")
    
    for giver_id, receiver_id in game["results"].items():
        receiver_name = db["users"].get(receiver_id, "Участник")
        try:
            bot.send_message(giver_id, f"🎁 Вы Тайный Санта для: **{receiver_name}**!\n\n(Игра {game_id})", parse_mode='Markdown')
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {giver_id}: {e}")

# ==========================================
# 4. ЗАПУСК БОТА
# ==========================================
if __name__ == '__main__':
    print("Бот запущен и готов к работе...")
    bot.infinity_polling()
