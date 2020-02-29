import random
import asyncio
import json
import logging
import aiohttp
# import requests
# import time
import os


class VkApi:
    def __init__(self, key, version):
        self.token = key
        self.v = version
        self.vk_url = "https://api.vk.com/method/"

    async def request_get(self, method, parameters=None, session=None):
        if not session:
            async with aiohttp.ClientSession() as session:
                return await self.request_get(method, parameters, session)

        if not parameters:
            parameters = {'access_token': self.token, 'v': self.v}
        if 'access_token' not in parameters:
            parameters.update({'access_token': self.token})
        if 'v' not in parameters:
            parameters.update({'v': self.v})

        try:
            async with session.post(self.vk_url + method, data=parameters) as response:
                if response.status == 200:
                    request = await response.json()
                    if request.get('error', {'error_code': 0})['error_code'] == 6:  # too many requests
                        return self.request_get(method, parameters)
                    return request
                else:
                    logging.error(f'request.status_code = {response.status}')
                    await asyncio.sleep(5)
                    return self.request_get(method, parameters, session)

        except aiohttp.ClientConnectionError as error_msg:
            logging.error(f'connection problems {error_msg}')
            await asyncio.sleep(5)
            return self.request_get(method, parameters, session)

        except Exception as error_msg:
            logging.error(f'{error_msg}')
            return {}

    async def msg_get(self, msg_id):
        msg = await self.request_get('messages.getById', {'message_ids': msg_id})
        logging.debug(f'message get {msg}')
        if 'response' in msg:
            return msg['response']['items'][0]
        else:
            return None

    async def msg_send(self, payload):
        payload['random_id'] = payload.get('random_id', random.randint(0, 2 ** 64))
        if type(payload.get('attachment', '')) != str:
            payload['attachment'] = ','.join(payload['attachment'])
        msg = await self.request_get('messages.send', payload)
        logging.debug(f'send message {msg}')
        if 'response' in msg:
            return msg['response']
        else:
            return None

    async def msg_read(self, peer_id):
        msg = await self.request_get('messages.markAsRead', {'peer_id': peer_id})
        logging.debug(f'read chat {msg}')
        if 'response' in msg:
            return msg['response']
        else:
            return None

    async def upload_image(self, image_url, peer_id=0, default_image=''):
        dir_path = os.path.abspath('img')
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        async with aiohttp.ClientSession() as session:
            upload_server = await self.request_get('photos.getMessagesUploadServer',
                                                   {'peer_id': peer_id}, session)
            if 'response' not in upload_server:
                logging.error(f'upload_server: {upload_server}')
                return default_image
            upload_url = upload_server['response']['upload_url']
            filename = os.path.join(dir_path, image_url.split('/')[-1])

            async with session.get(image_url) as resp:
                if resp.status == 200:
                    image = await resp.read()
                    with open(filename, "wb") as f:
                        f.write(image)
                else:
                    logging.error(f'download file: {resp.status}')
                    return default_image
            file = {'photo': open(filename, 'rb')}
            async with session.post(upload_url, data=file) as upload_image:
                if resp.status == 200:
                    upload_response = json.loads(await upload_image.text())
                else:
                    logging.error(f'download file: {resp.status}')
                    return default_image
            os.remove(filename)

            save_image = await self.request_get('photos.saveMessagesPhoto', {
                'photo': upload_response['photo'],
                'server': upload_response['server'],
                'hash': upload_response['hash'],
            }, session)
            if 'response' not in save_image:
                logging.error(f'save_image: {save_image}')
                return default_image
            # print('save_image', save_image)
            vk_image = save_image['response'][0]
            return f"photo{vk_image['owner_id']}_{vk_image['id']}_{vk_image['access_key']}"

    async def get_groups_info(self, group_ids, fields=''):
        msg = await self.request_get('groups.getById', {'group_ids': group_ids,
                                                        'fields': fields})
        if 'response' in msg:
            logging.debug(f'get groups info {msg}')
            return msg['response']
        else:
            logging.error(f'get groups info {msg}')
            return []

    async def get_users_info(self, user_ids, fields=''):
        msg = await self.request_get('users.get', {'user_ids': user_ids,
                                                   'fields': fields})
        if 'response' in msg:
            logging.debug(f'get users info {msg}')
            return msg['response']
        else:
            logging.error(f'get users info {msg}')
            return []

    async def get_admins(self):
        code = '''
        var group_id = API.groups.getById()[0].id;
        var admins = API.groups.getMembers({"group_id": group_id, "filter": "managers"});
        return admins.items;
        '''
        admins = await self.request_get('execute', {'code': code})
        if 'response' not in admins:
            logging.error(f'get admins error {admins}')
            return []
        return admins['response']


