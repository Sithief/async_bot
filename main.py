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
    handlers=[logging.FileHandler('log/bot.log', 'w', 'utf-8')]
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


def timer(timers, title):
    timers[title] = time.time() - timers['prew_timer']
    timers['prew_timer'] = time.time()


async def vk_analyze(params):
    timers = {'prew_timer': time.time()}
    from database import db_api
    timer(timers, 'import')
    message = UserMessage(
        peer_id=params['peer_id'],
        message_id=params['id'],
        text=params.get('text', ''),
        attachments=params.get('attachments', []),
        payload=json.loads(params['payload']) if params.get('payload') else None
    )
    timer(timers, 'input_message')
    msg_read = asyncio.create_task(vk.msg_read(message.peer_id))
    if params.get('is_cropped'):
        new_params = await vk.msg_get(params['id'])
        message.attachments = new_params.get('attachments', [])

    if not db_api.User.get_or_none(id=message.peer_id):
        menu = getattr(system.Functions(), 'new_user')

    elif message.payload:
        if TMP_MESSAGES.get(message.peer_id):
            message.unprocessed_messages = TMP_MESSAGES[message.peer_id]
            TMP_MESSAGES.pop(message.peer_id)
        menu = getattr(system.Functions(), message.payload[-1].get('mid', 'no_menu'), 'no_menu')

    elif message.text == 'restart':
        menu = getattr(system.Functions(), 'main')

    else:
        TMP_MESSAGES.setdefault(message.peer_id, list()).append(message)
        menu = None

    timer(timers, 'get_menu')
    if menu:
        bot_message = await menu(message)
        timer(timers, 'process_menu')
        await msg_read
        timer(timers, 'read_message')
        print(f'msg_to_send: {bot_message.convert_to_vk()}')
        send_message = await vk.msg_send(bot_message.convert_to_vk())
        timer(timers, 'send_message')
        logging.info(f'msg send: {send_message}')
        print(f'msg send: {send_message}, time: {round(time.time() - message.recieve_time, 3)}s.')
        if send_message:
            STATS['msg_send'] += 1

    else:
        await msg_read
        timer(timers, 'read_message')
    print(timers)


@routes.post('/vk_callback/')
async def vk_callback(request):
    if "application/json" in request.headers["Content-Type"]:
        request_json = await request.json()
        if request_json.get('type') == 'confirmation':
            confirm = CONF.get('VK', 'confirm', fallback='')
            return web.Response(text=confirm)

        elif request_json.get('type') == 'message_new':
            STATS['msg_get'] += 1
            new_message = request_json.get('object').get('message')
            asyncio.create_task(vk_analyze(new_message))
    return web.Response(text="Ok")


@routes.get('/')
async def index(request):
    uptime_days = int(time.time() - STATS['start_time']) // (24 * 60 * 60)
    uptime = time.strftime('%X', time.gmtime(time.time() - STATS['start_time']))

    return web.Response(text=f"server uptime: {uptime_days} days and {uptime}\n"
                             f"messages get: {STATS['msg_get']}\n"
                             f"messages send: {STATS['msg_send']}")


if __name__ == '__main__':
    from database import db_api
    if not db_api.init_db():
        db_api.update_db()
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(vk.get_admins())]
    done, _ = ioloop.run_until_complete(asyncio.wait(tasks))
    admins = list(done)[0].result()
    db_api.update_admins(admins)
    ioloop.create_task(system.post_arts())

    STATS = {
        'start_time': time.time(),
        'msg_get': 0,
        'msg_send': 0
     }
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=5000)
