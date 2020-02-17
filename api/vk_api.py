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
        logging.info(f'message get {msg}')
        if 'response' in msg:
            return msg['response']['items'][0]
        else:
            return None

    async def msg_send(self, payload):
        payload['random_id'] = payload.get('random_id', random.randint(0, 2 ** 64))
        if type(payload.get('attachment', '')) != str:
            payload['attachment'] = ','.join(payload['attachment'])
        msg = await self.request_get('messages.send', payload)
        logging.info(f'send message {msg}')
        if 'response' in msg:
            return msg['response']
        else:
            return None

    async def msg_read(self, peer_id):
        msg = await self.request_get('messages.markAsRead', {'peer_id': peer_id})
        logging.info(f'read chat {msg}')
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

# class Api(object):
#     def __init__(self, access_token, name='name', version='5.101'):
#         self.vk_url = "https://api.vk.com/method/"
#         self.token = access_token
#         self.name = name
#         self.version = version
#         self.VK_API = requests.Session()
#         logging.info(f'{self.name} gApi started')
#         self.valid = 'response' in self.request_get('utils.getServerTime')
#
#     def request_get(self, method, parameters=None):
#         if not parameters:
#             parameters = {'access_token': self.token, 'v': self.version}
#         if 'access_token' not in parameters:
#             parameters.update({'access_token': self.token})
#         if 'v' not in parameters:
#             parameters.update({'v': self.version})
#
#         try:
#             request = self.VK_API.post(self.vk_url + method, parameters, timeout=10)
#             if request.status_code == 200:
#                 if request.json().get('error', {'error_code': 0})['error_code'] == 6:  # too many requests
#                     return self.request_get(method, parameters)
#                 return request.json()
#             else:
#                 logging.error(f'request.status_code = {request.status_code}')
#                 time.sleep(5)
#                 return self.request_get(method, parameters)
#
#         except requests.exceptions.RequestException as error_msg:
#             logging.error(f'connection problems {error_msg}')
#             time.sleep(5)
#             return self.request_get(method, parameters)
#
#         except Exception as error_msg:
#             logging.error(f'{error_msg}')
#             return {}
#
#     def msg_send(self, peer_id, payload):
#         payload['peer_id'] = payload.get('peer_id', peer_id)
#         payload['random_id'] = payload.get('random_id', random.randint(0, 2 ** 64))
#         if type(payload.get('attachment', '')) != str:
#             payload['attachment'] = ','.join(payload['attachment'])
#         if type(payload.get('keyboard', '')) != str:
#             payload['keyboard'] = keyboard_from_buttons(payload['keyboard'])
#         msg = self.request_get('messages.send', payload)
#         logging.info(f'send message {msg}')
#         if 'response' in msg:
#             return msg['response']
#         else:
#             return False
#
#     def msg_get(self, message_id):
#         msg_info = self.request_get('messages.getById', {'message_ids': message_id})
#         if 'response' not in msg_info:
#             logging.error(f'get message error {msg_info}')
#             return {}
#         return msg_info['response']['items'][0]
#
#     def get_user_info(self, user_id):
#         user_info = self.request_get('users.get', {'user_ids': user_id, 'fields': 'sex'})
#         if 'response' not in user_info:
#             logging.error(f'get user error {user_info}')
#             return {}
#         return user_info['response'][0]
#
#     def get_group_info(self, group_id):
#         group_info = self.request_get('groups.getById', {'group_id': group_id,
#                                                          'fields': 'age_limits,has_photo,links,members_count'})
#         if 'response' not in group_info:
#             logging.error(f'get group error {group_info}')
#             return {}
#         return group_info['response'][0]
#
#     def upload_photo(self, peer_id, filename):
#         upload_server = self.request_get('photos.getMessagesUploadServer', {'peer_id': peer_id})
#         if 'response' not in upload_server:
#             logging.error(f'get upload server error {upload_server}')
#             return {}
#
#         url = upload_server['response']['upload_url']
#         file = {'photo': open(filename, 'rb')}
#         uploading_file = requests.post(url, files=file).json()
#
#         saving_photo = self.request_get('photos.saveMessagesPhoto', {'photo': uploading_file['photo'],
#                                                                      'server': uploading_file['server'],
#                                                                      'hash': uploading_file['hash']})
#         if 'response' not in saving_photo:
#             logging.error(f'get saving photo error {saving_photo}')
#             return {}
#         print('saved photo:', saving_photo['response'][0])
#         return ['photo%s_%s_%s' % (saving_photo['response'][0]['owner_id'],
#                                    saving_photo['response'][0]['id'],
#                                    saving_photo['response'][0]['access_key'])]
#
#     def messages_count(self, peer_id):
#         script = '''var peer_id=%d;
#                     var count=200;
#
#                     var history=API.messages.getHistory({"count":count, "peer_id":peer_id}).items;
#                     var time=API.utils.getServerTime();
#                     var msg_count=0;
#                     var iter=0;
#
#                     while (iter<count)
#                     {
#                         if (history[iter].out == 1 && time-history[iter].date < 3600)
#                         {
#                             msg_count = msg_count + 1;
#                         }
#                         iter = iter + 1;
#                     }
#                     return msg_count;''' % peer_id
#         msg_count = self.request_get('execute', {'code': script})
#         if 'response' not in msg_count:
#             logging.error(f'msg count error {msg_count}')
#             return 100
#         return msg_count['response']
#
#     def get_admins(self):
#         code = '''
# var group_id = API.groups.getById()[0].id;
# var admins = API.groups.getMembers({"group_id": group_id, "filter": "managers"});
# return admins.items;
# '''
#         admins = self.request_get('execute', {'code': code})
#         if 'response' not in admins:
#             logging.error(f'get admins error {admins}')
#             return []
#         return admins['response']
#
#     def send_notification(self, peer_id, payload):
#         last_message = self.request_get('messages.getHistory', {'count': 1, 'peer_id': peer_id})
#         if 'response' not in last_message:
#             logging.error(last_message)
#             return False
#         items = last_message['response']['items']
#         if items and time.time() - items[0]['date'] > 60 * 60:
#             return self.msg_send(peer_id, payload)
#
#
# class UserApi(object):
#     def __init__(self, access_token, group_id, last_reques_time, name='name', version='5.92'):
#         self.vk_url = "https://api.vk.com/method/"
#         self.token = access_token
#         self.group_id = group_id
#         self.last_request = last_reques_time
#         self.name = name
#         self.version = version
#         self.VK_API = requests.Session()
#         self.log_write('%s uApi started' % self.name, '%s uApi started' % self.name)
#
#     def log_write(self, log_file_text, log_console_text):
#         log_time = time.localtime(time.time())
#         log_console_text = '%02d:%02d:%02d | %s' % (log_time.tm_hour,
#                                                     log_time.tm_min,
#                                                     log_time.tm_sec,
#                                                     log_console_text)
#         print(log_console_text)
#         try:
#             log_file_text = '%02d.%02d.%02d %02d:%02d:%02d | %s\n' % (log_time.tm_mday,
#                                                                       log_time.tm_mon,
#                                                                       log_time.tm_year % 100,
#                                                                       log_time.tm_hour,
#                                                                       log_time.tm_min,
#                                                                       log_time.tm_sec,
#                                                                       log_file_text)
#             log_file = open(os.path.dirname(os.path.realpath(__file__)) + '/log/' + self.name + '_log.txt',
#                             'a', encoding='utf-8')
#             log_file.write(log_file_text)
#             log_file.close()
#         except Exception as e:
#             print("Can't write log to file!", str(e))
#
#     def request_get(self, method, parameters=None):
#         # print('request_get                     ', end='\r')
#         if not parameters:
#             parameters = {}
#         if 'access_token' not in parameters and 'v' not in parameters:
#             parameters.update({'access_token': self.token, 'v': self.version})
#         elif 'access_token' not in parameters:
#             parameters.update({'access_token': self.token})
#         elif 'v' not in parameters:
#             parameters.update({'v': self.version})
#
#         while time.time() - self.last_request.get_time() < 0.4:
#             time.sleep(random.random() % 0.4)
#         self.last_request.update()
#
#         try:
#             request = self.VK_API.post(self.vk_url + method, parameters, timeout=60)
#             if request.status_code == 200:
#                 if 'error' in request.json():
#                     error_code = request.json()['error']['error_code']
#                     if error_code in [1, 6, 10]:
#                         return self.request_get(method, parameters)
#                     self.log_write('request.json() %s' % (request.json()),
#                                    'request.json() %s' % (request.json()))
#
#                 return request.json()
#             else:
#                 self.log_write('request.status_code = ' + str(request.status_code),
#                                'request.status_code = ' + str(request.status_code))
#                 time.sleep(1)
#                 return self.request_get(method, parameters)
#
#         except requests.exceptions.RequestException as e:
#             self.log_write('connection problems: ' + str(e), 'connection problems')
#             time.sleep(5)
#             return self.request_get(method, parameters)
#
#         except Exception as e:
#             self.log_write('request_get: ' + str(e), 'request: ' + str(e))
#             return {}
#
#     def can_user_post(self, user_or_group_id, posts_before=5, posts_count=100):
#         next_posts = self.request_get('wall.get', {'owner_id': self.group_id * -1,
#                                                    'count': posts_count, 'filter': 'postponed'})
#         if 'response' not in next_posts:
#             self.log_write('next_posts: ' + str(next_posts),
#                            'next_posts: ' + str(next_posts))
#             return {'can_post': False, 'count': len(next_posts['response']['items'])}
#
#         if next_posts['response']['count'] >= posts_count:
#             return {'can_post': False, 'count': len(next_posts['response']['items'])}
#
#         if [i for i in next_posts['response']['items'] if str(user_or_group_id) in i['text']]:
#             return {'can_post': False, 'count': len(next_posts['response']['items'])}
#
#         last_posts = self.request_get('wall.get', {'owner_id': self.group_id * -1, 'count': posts_before})
#         if 'response' not in last_posts:
#             self.log_write('last_post: ' + str(last_posts),
#                            'last_post: ' + str(last_posts))
#             return {'can_post': False, 'count': len(next_posts['response']['items'])}
#         if [i for i in last_posts['response']['items'] if str(user_or_group_id) in i['text']]:
#             return {'can_post': False, 'count': len(next_posts['response']['items'])}
#
#         return {'can_post': True, 'count': len(next_posts['response']['items'])}
#
#     def create_post(self, text='', attachments=(), attachments_url=(), time_bp=60*60):
#         last_post = self.request_get('wall.get', {'owner_id': self.group_id * -1, 'count': 2})
#         if 'response' not in last_post:
#             self.log_write('last_post: ' + str(last_post),
#                            'last_post: ' + str(last_post))
#             return False
#         last_post = max(last_post['response']['items'], key=lambda x: x['date'])
#         next_posts = self.request_get('wall.get', {'owner_id': self.group_id * -1, 'count': 100, 'filter': 'postponed'})
#         if 'response' not in next_posts:
#             self.log_write('next_posts: ' + str(next_posts),
#                            'next_posts: ' + str(next_posts))
#             return False
#         time_to_post = (time.time() // 60 + 2) * 60
#         if last_post['date'] + time_bp > time_to_post:
#             time_to_post = last_post['date'] + time_bp
#
#         if next_posts['response']['count']:
#             next_posts = next_posts['response']['items']
#             while [1 for i in next_posts if abs(i['date'] - time_to_post) < time_bp]:
#                 time_to_post += time_bp
#
#         if attachments_url:
#             attachments_url_updated = self.upload_photos(attachments_url)
#             if len(attachments_url_updated) != len(attachments_url):
#                 return False
#         else:
#             attachments_url_updated = []
#
#         new_post = self.request_get('wall.post',
#                                     {'owner_id': self.group_id * -1,
#                                      'from_group': 1,
#                                      'message': text,
#                                      'attachments': ','.join(list(attachments) + attachments_url_updated),
#                                      'publish_date': time_to_post})
#         if 'response' not in new_post:
#             self.log_write('new_post: ' + str(new_post),
#                            'new_post: ' + str(new_post))
#             return False
#         return [time_to_post - time.time(), 'wall%s_%s' % (self.group_id * -1, new_post['response']['post_id'])]
#
#     def upload_photos(self, urls):
#         files = []
#         for num, url in enumerate(urls):
#             r = requests.get(url)
#             if r.status_code == 200 or r.status_code == 504:
#                 open(os.path.dirname(os.path.realpath(__file__)) + '/img/%s.jpg' % num, 'wb').write(r.content)
#                 files.append(os.path.dirname(os.path.realpath(__file__)) + '/img/%s.jpg' % num)
#             else:
#                 return []
#
#         uploaded_files = []
#         for filename in files:
#             upload_server = self.request_get('photos.getWallUploadServer', {'group_id': self.group_id})
#             if 'response' not in upload_server:
#                 self.log_write('upload_server: ' + str(upload_server),
#                                'upload_server: ' + str(upload_server))
#                 return []
#
#             url = upload_server['response']['upload_url']
#             upload_file = {'photo': open(filename, 'rb')}
#             uploading_file = requests.post(url, files=upload_file).json()
#             saving_photo = self.request_get('photos.saveWallPhoto', {'group_id': self.group_id,
#                                                                      'photo': uploading_file['photo'],
#                                                                      'server': uploading_file['server'],
#                                                                      'hash': uploading_file['hash']})
#             if 'response' not in saving_photo:
#                 self.log_write('saving_photo: ' + str(saving_photo),
#                                'saving_photo: ' + str(saving_photo))
#                 return []
#             uploaded_files.append('photo%s_%s_%s' % (saving_photo['response'][0]['owner_id'],
#                                                      saving_photo['response'][0]['id'],
#                                                      saving_photo['response'][0]['access_key']))
#         return uploaded_files
#
#     def upload_sticker(self, filename):
#         upload_server = self.request_get('docs.getUploadServer', {'type': 'graffiti', 'group_id': self.group_id})
#         if 'response' not in upload_server:
#             self.log_write('file_upload_server: ' + str(upload_server),
#                            'file_upload_server: ' + str(upload_server))
#             return {}
#
#         url = upload_server['response']['upload_url']
#         file = {'file': open(filename, 'rb')}
#         print('file', file)
#         uploading_file = requests.post(url, files=file).json()
#         print('uploading_file', uploading_file)
#
#         saving_file = self.request_get('docs.save', {'file': uploading_file['file'],
#                                                      'title': 'Artists_Hub',
#                                                      'tags': 'Artists_Hub'})
#         if 'response' not in saving_file:
#             self.log_write('saving_file: ' + str(saving_file),
#                            'saving_file: ' + str(saving_file))
#             return {}
#         print('saved file:', saving_file['response'])
#         return 'doc%s_%s' % (saving_file['response']['graffiti']['owner_id'], saving_file['response']['graffiti']['id'])
#
#
# def new_button(label, button, color='default'):
#     return {'action': {'type': 'text',
#                        'payload': button,
#                        'label': label},
#             'color': color}
#
#
# def get_actions_from_buttons(buttons):
#     actions = []
#     for buttons_row in buttons:
#         for button in buttons_row:
#             actions.append(button['action']['payload'])
#     return actions
#
#
# def keyboard_from_buttons(buttons):
#     keyboard = {#'one_time': True,
#                 'inline': True,
#                 'buttons': []}
#     for buttons_row in buttons:
#         if len(buttons_row) > 4:
#             if len(buttons_row) % 4:
#                 steps = len(buttons_row) // 4 * 4
#                 keyboard['buttons'] += [buttons_row[i:i + 4] for i in range(0, steps, 4)] + [buttons_row[steps:]]
#             else:
#                 steps = len(buttons_row) // 4 * 4
#                 keyboard['buttons'] += [buttons_row[i:i + 4] for i in range(0, steps, 4)]
#         elif len(buttons_row) > 0:
#             keyboard['buttons'].append(buttons_row)
#
#     for key_row in keyboard['buttons']:
#         for key in key_row:
#             if type(key['action']['payload']) != str:
#                 key['action']['payload'] = json.dumps(key['action']['payload'], ensure_ascii=False)
#     return json.dumps(keyboard, ensure_ascii=False)
