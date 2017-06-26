import requests
import json
import telebot
import conf
import flask
from telebot import types
import random
import pandas as pd
import re

WEBHOOK_URL_BASE = "https://{}:{}".format(conf.WEBHOOK_HOST, conf.WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(conf.TOKEN)

bot = telebot.TeleBot(conf.TOKEN, threaded=False)

bot.remove_webhook()

bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH)

app = flask.Flask(__name__)

global new_question
new_question = {"question_id": None,"name": None, "media": None, "question": None,"answers": None, "isOpen": None}


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.send_message(message.chat.id, "Здравствуйте! Это бот, который просит вас ответить на вопрос #чтозапредмет")
	bot.send_message(message.chat.id, "Все вопросы были составлены Борисом Иомдиным (vk.com/iomdin)")
	bot.send_message(message.chat.id, "Ещё бот умеет показывать вам статитстику для вопросов, на которые вы уже ответили /stats")


@bot.message_handler(commands=['new_question'])
def ask_question(message):
	media, question, answers, question_id = get_question(message.chat.id)
	if answers:
		for el in media:
			try:
				bot.send_document(message.chat.id, el)
			except:
				bot.send_photo(message.chat.id, el)
		keyboard = types.ReplyKeyboardMarkup()
		for el in answers:
			keyboard.add(types.KeyboardButton(el))

		if new_question['isOpen']:
			keyboard.add(types.KeyboardButton('другой ответ'))

		answer = bot.send_message(message.chat.id, question, reply_markup=keyboard)
		bot.register_next_step_handler(answer, get_answer)
	else:
		bot.send_message(message.chat.id, question)


@bot.message_handler(commands=['stats'])
def get_statistics(message):
	questions = get_answered_questions(message.chat.id)
	if type(questions) == str:
		bot.send_message(message.chat.id, questions)
	else:
		titles = get_questions_titles(questions.columns.tolist())
		question = 'Выберите вопрос:\n'
		keyboard = types.ReplyKeyboardMarkup()
		for column in questions.columns:
			keyboard.add(types.KeyboardButton(column))
			question += '%s %s\n' % (column, titles[column])
		answer = bot.send_message(message.chat.id, question, reply_markup=keyboard)
		bot.register_next_step_handler(answer, get_statistics_for_question)


def get_statistics_for_question(message):
	results = get_question_results(message.text)
	for result in results:
		res = re.search('^(.*?) ([.0-9]*)$', result)
		answer, percentage = res.group(1), res.group(2)
		percentage = float(percentage) * 100
		line = '%s %d' % (answer, int(percentage)) 
		bot.send_message(message.chat.id, line + '%')
	bot.send_message(message.chat.id, 'Вы хотите поучаствовать ещё в одном опросе? /new_question')
	bot.send_message(message.chat.id, 'Или узнать статистику? /stats')


def get_questions_titles(numbers):
	titles = {}
	with open('polls.json', 'r', encoding='utf-8') as f:
		polls = json.loads(f.read())
	for poll in polls:
		if str(poll['question_id']) in numbers:
			titles[str(poll['question_id'])] = poll['name']
	return titles


def get_answer(message):
	if message.text == 'другой ответ':
		answer = bot.send_message(message.chat.id, 'Введите ваш ответ:')
		bot.register_next_step_handler(answer, get_answer)
	else:
		save_answer(message.text, message.chat.id, new_question['question_id'])
		bot.send_message(message.chat.id, 'Хотите ещё вопрос? /new_question')
		bot.send_message(message.chat.id, 'Можно посмотреть статистику /stats')


def add_user(chat_id, users):
	users.loc[chat_id] = ['0' for i in range(15)]
	users.to_csv('users.csv')
	return users


def save_answer(answer, chat_id, question_id):
	users = pd.read_csv('users.csv', index_col='user_id')  
	users.ix[chat_id, str(question_id)] = answer
	users.to_csv('users.csv')


def get_question_results(number):
	users = pd.read_csv('users.csv', index_col='user_id')
	results_question = users[users[number] != '0'][number]
	if len(results_question) < 40:
		return get_question_results_iomdin(number)
	return str(results_question.value_counts(normalize = True)).split('\n')[:-1]


def get_question_results_iomdin(number):
	with open('iomdin_results.json', 'r', encoding='utf-8') as f:
		results = json.loads(f.read())
	for result in results:
		if result['id'] == number:
			return result['answers']


def get_answered_questions(chat_id):
	users = pd.read_csv('users.csv', index_col='user_id')
	if chat_id in users.index:
		questions = users
		columns = questions.columns.tolist()
		for column in columns:
			if questions.loc[chat_id][str(column)] == 0:
				questions = questions.drop(column, axis=1)
		if questions.columns.tolist() != []:
			return questions
	message = 'Чтобы посмотреть статистику, вам нужно ответить хотя бы на один вопрос /new_question'
	return message


def get_possible_questions(chat_id, users):
	if chat_id not in users.index:
		users = add_user(chat_id, users)
	with open('polls.json', 'r', encoding='utf-8') as f:
		polls = json.loads(f.read())
	questions = []
	for i, poll in enumerate(polls):
		if users.loc[chat_id][str(i)] in {0, '0'}:
			questions.append(poll)
	return questions


def get_question(chat_id):
	users = pd.read_csv('users.csv', index_col='user_id')
	polls = get_possible_questions(chat_id, users)
	if polls:
		question = random.choice(polls)
		global new_question
		new_question = question
		return question['media'], question['question'], question['answers'], question['question_id'] 
	else:
		no_more_questions = 'Ура! Вы поучаствовали во всех опросах. Не хотите посмотреть статистику? /stats'
		return None, no_more_questions, None, None


@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'ok'


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


if __name__ == '__main__':
	bot.polling(none_stop=True)