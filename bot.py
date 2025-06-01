from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import StateFilter
import json


TOKEN = ''
bot = TeleBot(TOKEN)

class KeyboardsState(StatesGroup):
    current_answers_state = State() # Состояние какое-то когда определяет правильный ответ и вызвает след. вопрос
    create_test = State() # Состояние для создания теста
    send_keyboard = State() # Состояние для выбора пользователем следующих действий
    buttons_count = State()
    create_question = State()
    create_answers = State()
    create_true_answers = State()

def gen_markup(buttons_info):
    # Создаём объект клавиатуры.
    keyboard = InlineKeyboardMarkup()

    for text_keyboard, callback_keyboard in buttons_info.items():
        # Создаём объект кнопки и добавляем её к клавиатуре.
        button = InlineKeyboardButton(
            text=text_keyboard, callback_data=callback_keyboard
        )
        keyboard.add(button)

    return keyboard

@bot.message_handler(commands=["start"])
def start_message(message):
    buttons = {'Пройти тест' : 'go',
                'Создать тест' : 'create'}
    bot.send_message(
        message.from_user.id,
        "Что вы хотите сделать?",
        reply_markup=gen_markup(buttons))  # Отправляем клавиатуру.

# БЛОК ДЛЯ ПРОХОЖДЕНИЯ ТЕСТОВ
@bot.callback_query_handler(func=lambda call: call.data == "go")
def go(callback_query):
    bot.set_state(callback_query.from_user.id, KeyboardsState.send_keyboard)
    bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    with open('tests.json', 'r', encoding='utf-8') as file:
        tests = json.load(file)

    bot.send_message(
        callback_query.from_user.id,
        "Перечень тестов:",
        reply_markup=gen_markup({t: t for t in tests})
    )

@bot.callback_query_handler(func=None, state=KeyboardsState.send_keyboard)
def current_test(callback_query):
    bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    with bot.retrieve_data(callback_query.from_user.id) as data:
        with open('tests.json', 'r', encoding='utf-8') as file:
            tests = json.load(file)
        
        data['current_test'] = callback_query.data
        data['test_data'] = tests[data['current_test']]
        data['question_index'] = 0
        data['correct_answers'] = 0

    bot.set_state(callback_query.from_user.id, KeyboardsState.current_answers_state)
    ask_question(callback_query.from_user.id)

def ask_question(user_id):
    with bot.retrieve_data(user_id) as data:
        if data['question_index'] >= len(data['test_data']):
            bot.send_message(
                user_id,
                f"Тест завершен! Правильных ответов: {data['correct_answers']} из {len(data['test_data'])}."
            )

            bot.send_message(
                user_id,
                'Введите команду /start если хотите сделать что-то ещё :)')
            bot.delete_state(user_id)
            return

        question = list(data['test_data'].keys())[data['question_index']]
        options = data['test_data'][question]

    bot.send_message(
        user_id,
        question,
        reply_markup=gen_markup({a: a for a in options}))

@bot.callback_query_handler(func=None, state=KeyboardsState.current_answers_state)
def current_answers(callback_answer):
    bot.edit_message_reply_markup(
        callback_answer.from_user.id, 
        callback_answer.message.message_id)

    with bot.retrieve_data(callback_answer.from_user.id) as data:
        question = list(data['test_data'].keys())[data['question_index']]

        with open('answers_tests.json', 'r', encoding='utf-8') as file:
            answers_tests = json.load(file)

        if callback_answer.data == answers_tests[data['current_test']][question]:
            data['correct_answers'] += 1

        data['question_index'] += 1

    ask_question(callback_answer.from_user.id)

# БЛОК ДЛЯ СОЗДАНИЯ ТЕСТОВ
@bot.callback_query_handler(
    func=lambda callback_query: (
        callback_query.data == "create"))
def test_create(callback_query):
    bot.set_state(callback_query.from_user.id, KeyboardsState.create_test, callback_query.message.chat.id)

    bot.edit_message_reply_markup(
        callback_query.from_user.id, callback_query.message.message_id)
    bot.send_message(
        callback_query.from_user.id,
        'Введите название теста:')
    
@bot.message_handler(state=KeyboardsState.create_test)
def handle_buttons_count(message):
    with bot.retrieve_data(message.from_user.id) as data:
        with open('tests.json', 'r', encoding='utf-8') as file:
            tests = json.load(file)

        if message.text in tests:
            bot.send_message(
                message.from_user.id,
                'Тест с таким названием уже есть. Пожалуйста, придумайте другое название для теста.'
            )
        else:
            data['question'] = {}
            data['name test'] = message.text

            bot.set_state(
                message.from_user.id,
                KeyboardsState.buttons_count,
                message.chat.id)
            bot.send_message(
            message.from_user.id,
            'Отлично! Теперь введите количество вопросов')
        
@bot.message_handler(state=KeyboardsState.buttons_count)
def create_question_1(message):
        if message.text.isdigit():
            with bot.retrieve_data(message.from_user.id) as data:
                data['question count'] = int(message.text)
                data['count'] = 1

            bot.send_message(message.from_user.id, "Отлично!")
            bot.send_message(message.from_user.id, 
                             f"Введите текст вопроса №{data['count']}")

            bot.set_state(
                message.from_user.id,
                KeyboardsState.create_question,
                message.chat.id)

        else:
            bot.send_message(message.from_user.id, 
                             "Количество вопросов должно быть указано числом!")

@bot.message_handler(state=KeyboardsState.create_question)
def create_question_2(message):
    with bot.retrieve_data(message.from_user.id) as data:
        temp_question = []
        temp_question.append(message.text)
        data['temp question'] = temp_question

        if len(temp_question) == 1:
            data['count'] += 1
            data['question count'] -= 1

            bot.send_message(
                    message.from_user.id,
                    "Введите варианты ответов через запятую с пробелом (, )")
            
            bot.set_state(
            message.from_user.id,
            KeyboardsState.create_answers,
            message.chat.id)

@bot.message_handler(state=KeyboardsState.create_answers)
def create_answers(message):
    with bot.retrieve_data(message.from_user.id) as data:
        data['answers'] = []
        data['answers'] = message.text.split(', ')
        bot.send_message(
                    message.from_user.id,
                    'Введите номер правильного ответа (начиная с 1)')
        bot.set_state(
                message.from_user.id,
                KeyboardsState.create_true_answers,
                message.chat.id)
        
@bot.message_handler(state=KeyboardsState.create_true_answers)
def save_test(message):
    with open('tests.json', 'r', encoding='utf-8') as file:
        tests = json.load(file)
    with open('answers_tests.json', 'r', encoding='utf-8') as file:
        answers_tests = json.load(file)

    with bot.retrieve_data(message.from_user.id) as data:
        if int(message.text) > 0 and message.text.isdigit():
            if int(message.text) > len(data['answers']):
                print('BOBER')
                bot.send_message(
                        message.from_user.id,
                        'Это число больше, чем количество ответов. Введите корректное число.')
                
            else:
                if data['name test'] not in tests:
                    
                    # Вопрос и ответы на него
                    temp_question = data['temp question'][0]
                    question_and_answer_1 = {temp_question : data['answers']}

                    # Правильный вопрос и ответы на него
                    index_true_answer = int(message.text) - 1
                    true_answer = data['answers'][index_true_answer]
                    question_and_answer_2 = {temp_question : true_answer}

                    # Сохранение
                    tests[data['name test']] = question_and_answer_1
                    answers_tests[data['name test']] = question_and_answer_2

                    with open('tests.json', 'w', encoding='utf-8') as file:
                        json.dump(tests, file, ensure_ascii=False, indent=4)
                    with open('answers_tests.json', 'w', encoding='utf-8') as file:
                        json.dump(answers_tests, file, ensure_ascii=False, indent=4)

            temp_question = data['temp question'][0]
            tests[data['name test']][temp_question] = data['answers']

            index_true_answer = int(message.text) - 1
            true_answer = data['answers'][index_true_answer]
            answers_tests[data['name test']][temp_question] = true_answer

            with open('tests.json', 'w', encoding='utf-8') as file:
                json.dump(tests, file, ensure_ascii=False, indent=4)
            with open('answers_tests.json', 'w', encoding='utf-8') as file:
                json.dump(answers_tests, file, ensure_ascii=False, indent=4)

            bot.send_message(
                        message.from_user.id,
                        'Вопрос и ответы сохранены!')
            
            if not data['question count']:
                bot.send_message(message.from_user.id, 'Тест создан!')
                bot.send_message(
                                message.from_user.id,
                                'Введите команду /start если хотите сделать что-то ещё :)')
                bot.delete_state()

            else:
                bot.send_message(message.from_user.id, 
                                f"Введите текст вопроса №{data['count']}")
                bot.set_state(
                    message.from_user.id,
                    KeyboardsState.create_question,
                    message.chat.id)
        else:
            bot.send_message(message.from_user.id, 
                'Введите число больше 0!')

bot.add_custom_filter(StateFilter(bot))
bot.infinity_polling()