import json
import vk
from getpass import getpass


def api_session():
	user_login = input('login: ')
	user_password = getpass('password: ')
	session = vk.AuthSession(app_id=6065285, user_login=user_login, user_password=user_password)
	api = vk.API(session, v='5.65')
	return api


def download_polls(domain, query):
	polls = api_session().wall.search(domain=domain, query=query, owners_only=1, fields='poll')
	return polls['items']


def prepare_poll(post):
	isPoll = False
	new_poll = {'name': '', 'media': [], 'question': None, 'answers': [], 'isOpen': 0}
	for a in post['attachments']:
		if a['type'] == 'photo':
			new_poll['media'].append(a['photo']['photo_604'])
		if a['type'] == 'doc':
			new_poll['media'].append(a['doc']['url'])
		if a['type'] == 'poll':
			isPoll = True
			new_poll['question'] = a['poll']['question']
			for answer in a['poll']['answers']:
				if 'ругое' in answer['text'] or 'комментари' in answer['text']:
					new_poll['isOpen'] = 1
				else:
					new_poll['answers'].append(answer['text'])
	if isPoll:
		return new_poll
	else:
		return None


def get_only_polls(polls):
	polls_clean = []
	for post in polls:
		if 'attachments' in post:
			new_poll = prepare_poll(post)
			if new_poll:
				polls_clean.append(new_poll)
	return polls_clean


def get_polls(domain, query):
	polls = download_polls(domain, query)
	polls = get_only_polls(polls)
	return polls


def main():
	domain = 'iomdin'
	query = '#чтозапредмет'
	polls = get_polls(domain, query)
	with open('polls.json', 'w', encoding='utf-8') as f:
		json.dump(polls, f, ensure_ascii=False, indent = 4)


if __name__ == '__main__':
	main()