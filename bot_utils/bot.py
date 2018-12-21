import telebot
from bot_utils import config, bot_handlers, bot_methods
import game_classes
from fight import fight_main, units
import time, requests, threading
from chat_wars import chat_main
import test_2


start_time = time.time()
call_handler = bot_handlers.CallbackHandler()
game_dict = game_classes.game_dict
telebot.apihelper.proxy = {
  'https': 'http://178.33.39.70:3128'
}

types = telebot.types

bot = telebot.TeleBot(config.token, threaded=False)


@bot.message_handler(commands=["start"])
def game(message):
    if len(message.text.split(' ')) > 1:
        data = message.text.split(' ')[1].split('_')
        if int(data[1]) in game_classes.game_dict:
            game_classes.game_dict[int(data[1])].join_lobby(message.from_user.id, message.from_user.first_name)


@bot.message_handler(commands=["game"])
def game(message):
    if message.chat.id not in game_dict:
        game_classes.VsGame(message.chat.id, lang='rus' if message.from_user.language_code == 'ru-RU' else 'rus')
    else:
        game_dict[message.chat.id].error('game_exists')


@bot.message_handler(commands=["ffa"])
def game(message):
    if message.chat.id not in game_dict:
        game_classes.FFAGame(message.chat.id, lang='rus' if message.from_user.language_code == 'ru-RU' else 'rus')
    else:
        game_dict[message.chat.id].error('game_exists')


@bot.message_handler(commands=["join_dog"])
def join(message):
    try:
        if message.chat.id in game_dict:
            game_dict[message.chat.id].join_dog()
    except AttributeError:
        pass


@bot.message_handler(commands=["join_rat"])
def join(message):
    try:
        if message.chat.id in game_dict:
            game_dict[message.chat.id].join_rat()
    except AttributeError:
        pass


@bot.message_handler(commands=["join_zombie"])
def join(message):
    try:
        if message.chat.id in game_dict:
            game_dict[message.chat.id].join_zombie()
    except AttributeError:
        pass


@bot.message_handler(commands=["join_RAT"])
def join(message):
    try:
        if message.chat.id in game_dict:
            game_dict[message.chat.id].join_RAT()
    except AttributeError:
        pass


@bot.message_handler(commands=["switch"])
def switch(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].change_team(message.from_user.id)


@bot.message_handler(commands=['start_game'])
def start(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].ask_start()


@bot.message_handler(commands=['map'])
def start(message):
    thread = threading.Thread(target=game_classes.Dungeon, args=[message.chat.id, 'rus'])
    thread.start()


@bot.message_handler(commands=['test_fight'])
def start(message):
    # [team={chat_id:(name, unit_dict)} or team={(ai_class, n):(ai_class.name, unit_dict)}].
    name = message.from_user.first_name
    mob_class = fight_main.units.Snail
    fight_main.thread_fight(None, {message.from_user.id: (name, units.Human(name).to_dict())},
                                   {(mob_class, 1): (None, mob_class().to_dict())}, chat_id=message.chat.id)

@bot.message_handler(commands=['test'])
def start(message):
    smile_text = message.text.split()[-1]
    print(smile_text)
    output = (smile_text
              .encode('raw_unicode_escape')
              )
    bot_methods.send_message(message.chat.id, output)


@bot.message_handler(commands=['test_add_chat'])
def start(message):
    if message.chat.id < 0:
        chat_main.add_chat(message.chat.id, message.chat.title, message.from_user.id)


@bot.message_handler(commands=['start_attack'])
def start(message):
    print(message)
    if message.chat.id < 0:
        chat = chat_main.pyossession.get_chat(message.chat.id)
        chat.ask_attack(message.from_user.id)


@bot.message_handler(commands=['tst'])
def start(message):
    bot_methods.send_message(message.chat.id, test_2.message)


@bot.message_handler(content_types=['photo'])
def start(message):
    print(message.photo[0].file_id)


@bot.callback_query_handler(func=lambda call: call)
def action(call):
    call_handler.handle(call)

bot.skip_pending = True


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True)
        except requests.exceptions.ProxyError:
            time.sleep(8)
            pass