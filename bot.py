import requests
import time

session = requests.session()
# server = 'http://127.0.0.1:5000'
server = 'http://f57846aa.ngrok.io'


resp = session.post(server + '/vk_callback/', json={'type': 'confirmation', 'group_id': 123456})
print(resp.text)
time.sleep(1)
resp = session.post(server + '/vk_callback/', json={
    'type': 'message_new',
    'object': {
        'message': {
            'date': 1580840259,
            'from_id': 410050173,
            'id': 33537,
            'out': 0,
            'peer_id': 410050173,
            'text': 'g',
            'conversation_message_id': 21880,
            'fwd_messages': [],
            'important': False,
            'random_id': 0,
            'attachments': [],
            'is_hidden': False,
            'payload': '[{"mid": "main"}]'
        },
        'client_info': {
            'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link'],
            'keyboard': True,
            'inline_keyboard': True,
            'lang_id': 0
        }
    },
    'group_id': 165142388,
    'event_id': '9a55119f9f0194578fc4062ad9b23a4684db6d5d'
})
print(resp.text)
