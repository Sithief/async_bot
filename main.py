import asyncio
import logging
import configparser
import time
import json
from aiohttp import web
from api.vk_api import VkApi
from bot_menu import system

CONF = configparser.ConfigParser()
CONF.read('bot_settings.inf', encoding='utf-8')

routes = web.RouteTableDef()
vk = VkApi(CONF.get('VK', 'token', fallback=''), '5.103')
logging.basicConfig(
    format='%(filename)-25s[LINE:%(lineno)4d]# %(levelname)-8s [%(asctime)s]  %(message)s',
    level=logging.DEBUG,
    datefmt='%m-%d %H:%M',
    filename='log/bot.log',
    filemode='w'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-15s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class UserMessage:
    def __init__(self, peer_id, message_id, text='', attachments=(), payload=None):
        self.peer_id = peer_id
        self.message_id = message_id
        self.text = text
        self.attachments = attachments
        self.payload = payload
        self.recieve_time = time.time()
        self.unprocessed_messages = []


TMP_MESSAGES = dict()


async def vk_analyze(params):
    message = UserMessage(
        peer_id=params['peer_id'],
        message_id=params['id'],
        text=params.get('text', ''),
        attachments=params.get('attachments', []),
        payload=json.loads(params['payload']) if params.get('payload') else None
    )
    if params.get('attachments'):
        new_params = await vk.msg_get(params['id'])
        message.attachments = new_params.get('attachments', [])
    await vk.msg_read(message.peer_id)
    if message.payload:
        if TMP_MESSAGES.get(message.peer_id):
            message.unprocessed_messages = TMP_MESSAGES[message.peer_id]
            TMP_MESSAGES.pop(message.peer_id)
        menu = getattr(system.Functions(), message.payload[-1]['mid'], 'no_menu')
        bot_message = await menu(message)
        send_message = await vk.msg_send(bot_message.convert_to_vk())
        logging.info(f'msg send: {send_message}')
        print(f'msg send: {send_message}, time: {round(time.time() - message.recieve_time, 3)}s.')
    else:
        TMP_MESSAGES.setdefault(message.peer_id, list()).append(message)


@routes.post('/vk_callback/')
async def vk_callback(request):
    if "application/json" in request.headers["Content-Type"]:
        request_json = await request.json()
        if request_json.get('type') == 'confirmation':
            confirm = CONF.get('VK', 'confirm', fallback='')
            return web.Response(text=confirm)

        elif request_json.get('type') == 'message_new':
            new_message = request_json.get('object').get('message')
            asyncio.create_task(vk_analyze(new_message))
    return web.Response(text="Ok")


@routes.get('/')
async def index(request):
    return web.Response(text="server up")


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=5000)
