import logging
import json
import asyncio
import time
import random
from main import vk
from database import db_api


class Button:
    def __init__(self, label, payload, color='default'):
        self.label = label
        self.payload = payload
        self.color = color


class Keyboard:
    def __init__(self, default_payload=None, buttons=None, inline=False, one_time=False, save_menu=True):
        self.buttons = buttons if buttons else [[]]
        self.one_time = one_time if not inline else False
        self.inline = inline
        self.save_menu = save_menu
        self.default_payload = []
        if default_payload:
            self.default_payload = default_payload if save_menu else default_payload[:-1]

    def add_button(self, label, payload, color='default', row=-1):
        new_payload = self.default_payload + [payload] if payload else self.default_payload
        new_button = Button(label, new_payload, color)
        if row >= len(self.buttons):
            self.buttons.extend([[] for _ in range(row - len(self.buttons) + 1)])
        self.buttons[row].append(new_button)

    def navigation_buttons(self, ):
        self.buttons.extend([[] for _ in range(10 - len(self.buttons) + 1)])
        if len(self.default_payload) > 1:
            if self.save_menu:
                self.buttons[10] = [Button('назад', self.default_payload[:-1])]
            else:
                self.buttons[10] = [Button('назад', self.default_payload)]
        self.buttons[10].append(Button('домой', self.default_payload + [{'mid': 'main'}]))

    def get_vk_keyboard(self):
        buttons = []
        for button_row in self.buttons:
            if button_row:
                buttons.append([])
                for button in button_row:
                    if self.inline and len(buttons[-1]) >= 3:
                        buttons.append([])
                    elif not self.inline and len(buttons[-1]) >= 4:
                        buttons.append([])
                    btn_payload = json.dumps(button.payload, ensure_ascii=False)
                    while len(btn_payload) > 255:
                        button.payload.pop(0)
                        btn_payload = json.dumps(button.payload, ensure_ascii=False)
                    new_button = {
                        'action': {
                            'type': 'text',
                            'label': button.label,
                            'payload': btn_payload
                        },
                        'color': button.color
                    }
                    buttons[-1].append(new_button)

        keyboard = {
            'one_time': self.one_time,
            'inline': self.inline,
            'buttons': buttons
        }
        return json.dumps(keyboard, ensure_ascii=False)


class BotMessage:
    def __init__(self, peer_id, text,  attachments=None, keyboard=None,
                 default_payload=None, save_menu=True):
        self.peer_id = peer_id
        self.text = text
        self.attachments = attachments if attachments else []
        self.keyboard = keyboard if keyboard else Keyboard(default_payload=default_payload, save_menu=save_menu)

    def convert_to_vk(self):
        return {
            'peer_id': self.peer_id,
            'message': self.text,
            'attachment': ','.join(self.attachments),
            'keyboard': self.keyboard.get_vk_keyboard()
        }


class AdminFunctions:
    async def change_tag_list(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Список тегов",
            default_payload=msg.payload
        )
        tags = db_api.Tag.select().limit(16)
        for t in tags:
            bot_message.keyboard.add_button(t.title, {'mid': 'change_tag', 'tid': t.id})
        bot_message.keyboard.add_button('Создать новый тег', {'mid': 'change_tag', 'new': True}, row=5)
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def change_tag(self, msg):
        if msg.payload[-1].get('new'):
            tag = db_api.Tag.create()
        else:
            tag = db_api.Tag.get_or_none(id=msg.payload[-1].get('tid', 0))

        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="",
            default_payload=msg.payload,
            save_menu=False
        )

        need_update = msg.payload[-1].get('new_text')
        if need_update:
            new_text = '\n'.join([m.text for m in msg.unprocessed_messages])
            if not new_text:
                bot_message.text = 'Введите текст, затем снова нажмите кнопку для сохранения'
            elif need_update == 'title':
                new_text = new_text.replace('\n', ' ')
                if len(new_text) > 35:
                    bot_message.text = 'Слишком длинное название для тега'
                else:
                    tag.title = new_text
                    tag.save()

            elif need_update == 'descr':
                tag.description = new_text
                tag.save()

        if bot_message.text == "":
            bot_message.text = f"Тег: \"{tag.title}\"\n" \
                               f"Описание:\n {tag.description}\n\n"

        bot_message.keyboard.add_button("Изменить название", {'mid': 'change_tag',
                                                              'tid': tag.id,
                                                              'new_text': 'title'})
        bot_message.keyboard.add_button("Изменить описание", {'mid': 'change_tag',
                                                              'tid': tag.id,
                                                              'new_text': 'descr'})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def confirm_group_list(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Список добавленных пользователями групп для подтверждения.",
            default_payload=msg.payload
        )
        groups = db_api.Group.select().where(db_api.Group.accepted == 0).limit(16)
        for g in groups:
            bot_message.keyboard.add_button(g.name[:35], {'mid': 'confirm_group',
                                                          'gid': g.id})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def confirm_group(self, msg):
        group_id = msg.payload[-1].get('gid')
        group = db_api.Group.get_or_none(id=group_id)
        group_link = f"@club{group.id} ({group.name})"
        user_link = f"@id{group.add_by.id} ({group.add_by.name})"
        images = db_api.Art.select().where(db_api.Art.from_group == group).limit(10)
        group_images = [i.vk_id for i in images]
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text=f"Группа {group_link} \n"
                 f"Добавил(а) {user_link}",
            default_payload=msg.payload,
            save_menu=False,
            attachments=group_images
        )
        group_accept = msg.payload[-1].get('accept')
        if group_accept == 1:
            group.accepted = 1
            group.save()
            bot_message.keyboard.add_button('Отклонить',
                                            {'mid': 'confirm_group',
                                             'gid': group_id,
                                             'accept': -1},
                                            color='negative')
        elif group_accept == -1:
            group.accepted = -1
            group.save()
            bot_message.keyboard.add_button('Одобрить',
                                            {'mid': 'confirm_group',
                                             'gid': group_id,
                                             'accept': 1},
                                            color='positive')
        else:
            bot_message.keyboard.add_button('Одобрить',
                                            {'mid': 'confirm_group',
                                             'gid': group_id,
                                             'accept': 1},
                                            color='positive')
            bot_message.keyboard.add_button('Отклонить',
                                            {'mid': 'confirm_group',
                                             'gid': group_id,
                                             'accept': -1},
                                            color='negative')
        bot_message.keyboard.navigation_buttons()

        return bot_message


class Functions(AdminFunctions):
    async def no_menu(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Ошибка доступа",
            default_payload=msg.payload
        )
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def new_user(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Приветствую тебя!",
            default_payload=[]
        )
        user_info = await vk.get_users_info(msg.peer_id, 'sex')
        if user_info:
            uinfo = user_info[0]
            db_api.User.create(id=uinfo['id'],
                               name=f"{uinfo['first_name']} {uinfo['last_name']}",
                               is_fem=uinfo.get('sex', 0) % 2)
        else:
            bot_message.text = 'Упс, при регистрации возникла какая-то ошибка'
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def main(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Сейчас вы в главном меню",
            default_payload=msg.payload
        )
        bot_message.keyboard.add_button('Добавить группу вручную', {'mid': 'add_group'})
        bot_message.keyboard.add_button(f"Найти новый арт", {'mid': 'add_image'}, row=2)
        user = db_api.User.get_or_none(id=msg.peer_id)
        is_admin = db_api.Admins.get_or_none(user=user)

        if is_admin:
            groups_count = db_api.Group.select().where(db_api.Group.accepted == 0).count()
            bot_message.keyboard.add_button(f"Одобрить группы ({groups_count})",
                                            {'mid': 'confirm_group_list'}, row=3)
            bot_message.keyboard.add_button(f"Список тегов",
                                            {'mid': 'change_tag_list'}, row=4)

        groups_count = db_api.Group.select().where(db_api.Group.accepted == 1).count()
        bot_message.keyboard.add_button(f"Группы художников ({groups_count})",
                                        {'mid': 'view_group_list'}, row=5)
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def add_group(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Отправьте 3 поста с рисунками художника.\n"
                 "Посты должны быть выложены не более 3 месяцев назад.\n"
                 "Если в посте более 1 изображения, будет сохранено только первое.\n"
                 "После отправки постов, нажмите кнопку \"сохранить\"",
            default_payload=msg.payload
        )
        bot_message.keyboard.add_button('сохранить', {'mid': 'save_group'})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def save_group(self, msg):
        posts = []

        for message in msg.unprocessed_messages:
            for attachment in message.attachments:
                if attachment['type'] != 'wall':
                    continue
                post = attachment['wall']
                if not post.get('from'):
                    groups_info = await vk.get_groups_info(-post['to_id'])
                    post['from'] = groups_info[0]
                posts.append(post)
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="",
            default_payload=msg.payload,
            save_menu=False
        )
        can_add, err_message = check_group_add_posts(posts)
        if not can_add:
            bot_message.text = err_message
            bot_message.keyboard.add_button('Попробовать снова', {'mid': 'add_group'})
        else:
            user = db_api.User.get_or_none(id=msg.peer_id)
            group_info = await vk.get_groups_info(-posts[0]['to_id'], 'members_count')
            print('group_info', group_info)
            group_info = group_info[0]
            likes = sum([i['likes']['count'] for i in posts]) / len(posts)
            views = sum([i['views']['count'] for i in posts]) / len(posts)
            group = db_api.Group.create(id=group_info['id'],
                                        name=group_info['name'],
                                        add_by=user,
                                        likes=likes,
                                        views=views,
                                        subs=group_info['members_count'],
                                        last_update=int(time.time()))
            vk_link = f"@club{group.id} ({group.name})"

            future_arts = list()
            for post in posts:
                photo = [a['photo'] for a in post['attachments'] if a['type'] == 'photo'][0]
                image_url = sorted(photo['sizes'], key=lambda x: x['width'] * x['height'])[-1]['url']
                source = f"wall{post['from_id']}_{post['id']}"
                task = asyncio.create_task(save_art(image_url=image_url,
                                                    source=source,
                                                    add_by=user,
                                                    from_group=group))
                future_arts.append(task)
            arts = [art for art, is_new in await asyncio.gather(*future_arts)]
            bot_message.text = f"Группа {vk_link} добавлена в базу.\n" \
                               f"После одобрения администратором её можно будет найти в общем списке."
            bot_message.attachments = [a.vk_id for a in arts]
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def view_group_list(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Список добавленных пользователями групп.",
            default_payload=msg.payload
        )
        offset = msg.payload[-1].get('offset', 0)
        groups = db_api.Group.select()\
            .where(db_api.Group.accepted == 1)\
            .order_by(db_api.Group.last_update.desc())\
            .offset(offset)\
            .limit(16)
        posts_count = db_api.Group.select().\
            where(db_api.Group.accepted == 1)\
            .count()
        for g in groups:
            bot_message.keyboard.add_button(
                g.name[:35], {'mid': 'view_group', 'gid': g.id}
            )
        bot_message.keyboard.add_button(
            '<-', {'mid': 'view_group_list', 'offset': max(offset-1, 0)}, row=5
        )
        bot_message.keyboard.add_button(
            '->', {'mid': 'view_group_list',
                   'offset': min(offset+1, posts_count//16)}, row=5
        )
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def view_group(self, msg):
        group = db_api.Group.get_or_none(id=msg.payload[-1].get('gid'))
        group_link = f"@club{group.id} ({group.name})"
        user_link = f"@id{group.add_by.id} ({group.add_by.name})"
        images = db_api.Art.select()\
            .where(db_api.Art.from_group == group) \
            .order_by(db_api.Art.add_time.desc()) \
            .limit(10)
        group_images = [i.vk_id for i in images]
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text=f"Группа {group_link} \n"
                 f"Добавил(а) {user_link}",
            default_payload=msg.payload,
            attachments=group_images
        )
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def add_image(self, msg):
        groups = db_api.Group.select()\
            .where(db_api.Group.accepted == 1)\
            .order_by(db_api.Group.last_update)\
            .limit(10)
        group = random.choice(groups)
        group_link = f"@club{group.id} ({group.name})"
        images = db_api.Art.select()\
            .where(db_api.Art.from_group == group) \
            .order_by(db_api.Art.add_time.desc()) \
            .limit(10)
        group_images = [i.vk_id for i in images]
        last_post = time.strftime('%d.%m.%y', time.localtime(group.last_post)) if group.last_post else "никогда..."
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text=f"Из группы {group_link} давно не было рисунков.\n"
                 f"Последнее обновление было {last_post}.\n"
                 f"Поищи пожалуйста пост с новой работой художника и перешли его сюда.\n"
                 f"Когда отправишь пост, нажми кнопку \"Сохранить пост\"",
            default_payload=msg.payload,
            attachments=group_images
        )
        bot_message.keyboard.add_button('Cохранить пост', {'mid': 'verify_image', 'gid': group.id})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def verify_image(self, msg):
        arts_tasks = []
        already_in_base = False
        wrong_group = False
        for message in msg.unprocessed_messages:
            for attachment in message.attachments:
                if attachment['type'] != 'wall':
                    continue
                elif -attachment['wall']['to_id'] != msg.payload[-1].get('gid'):
                    wrong_group = True
                    continue
                post_attachments = attachment['wall'].get('attachments', [])
                post_images = [i['photo'] for i in post_attachments if i['type'] == 'photo']
                for photo in post_images:
                    image_url = sorted(photo['sizes'], key=lambda x: x['width'] * x['height'])[-1]['url']
                    if len(arts_tasks) >= 10:
                        break
                    elif db_api.Art.get_or_none(url=image_url):
                        already_in_base = True
                        break
                    task = asyncio.create_task(prepare_art(image_url=image_url,
                                                           group_id=attachment['wall']['from_id'],
                                                           post_id=attachment['wall']['id']))
                    arts_tasks.append(task)
        arts = await asyncio.gather(*arts_tasks)
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="",
            default_payload=msg.payload,
            save_menu=False
        )
        if not arts:
            if already_in_base:
                bot_message.text = "Все эти арты уже есть в базе"
            elif wrong_group:
                bot_message.text = "Принимаются работы только из заданной группы"
            else:
                bot_message.text = f"Нужно отправить пост с артом"
            bot_message.keyboard.add_button('Попробовать снова', {'mid': 'add_image'})

        elif len(arts) == 1:
            bot_message.text = "Вы прислали это изображение, верно?"
            bot_message.attachments.append(arts[0]['art'])
            bot_message.keyboard.add_button(f'Сохранить арт', dict({'mid': 'save_art'}, **arts[0]), color='positive')

        else:
            bot_message.text = "Вы прислали несколько изображений, однако к посту можно прикрепить только одно.\n" \
                               "Выберите одно из изображений, чтобы продолжить"
            for num, art in enumerate(arts):
                bot_message.attachments.append(art['art'])
                bot_message.keyboard.add_button(f'арт: {num+1}', dict({'mid': 'save_art'}, **art))

        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def save_art(self, msg):
        source = f"wall-{msg.payload[-1].get('gid')}_{msg.payload[-1].get('pid')}"
        user = db_api.User.get_or_none(id=msg.peer_id)
        group = db_api.Group.get_or_none(id=msg.payload[-1].get('gid'))
        saved_art = db_api.Art.create(vk_id=msg.payload[-1].get('art'),
                                      url=msg.payload[-1].get('url'),
                                      source=source,
                                      add_by=user,
                                      from_group=group,
                                      add_time=time.time())
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Новый арт добавлен в базу.\n"
                 "Осталось только отметить подходящие теги",
            default_payload=msg.payload,
            save_menu=False,
            attachments=[saved_art.vk_id]
        )
        bot_message.keyboard.add_button('Добавить теги', {'mid': 'art_tags', 'aid': saved_art.id}, color='positive')
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def art_tags(self, msg):
        art = db_api.Art.get_or_none(id=msg.payload[-1].get('aid'))
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Зеленым отмечены выбранные теги.\n",
            default_payload=msg.payload,
            save_menu=False,
            attachments=[art.vk_id]
        )
        if msg.payload[-1].get('tid'):
            tag = db_api.Tag.get_or_none(id=msg.payload[-1].get('tid'))
            art_tag = db_api.ArtTag.get_or_none(art=art, tag=tag)
            if not art_tag and msg.payload[-1].get('add'):
                db_api.ArtTag.create(art=art, tag=tag)
            elif art_tag and not msg.payload[-1].get('add'):
                art_tag.delete().execute()

        all_tags = db_api.Tag.select().limit(16)
        selected_tags = [t.tag for t in db_api.ArtTag.select().where(db_api.ArtTag.art == art)]
        for t in all_tags:
            color = 'default'
            add = True
            if t in selected_tags:
                color = 'positive'
                add = False
            bot_message.keyboard.add_button(t.title, {'mid': 'art_tags',
                                                      'aid': art.id,
                                                      'tid': t.id,
                                                      'add': add}, color=color)
        bot_message.keyboard.navigation_buttons()
        return bot_message




def check_group_add_posts(posts):
    start_time = list(time.localtime(time.time()))
    start_time[1] -= 3
    start_time = time.mktime(tuple(start_time))
    min_posts = 3
    if len(posts) < min_posts:
        return False, f"Нужно отправить не менее {min_posts} постов"

    from_info = posts[0].get('from', {})
    if not from_info.get('type') in ['group', 'page']:
        return False, "Принимаются только посты из группы"

    if not all([-i.get('to_id') == from_info.get('id') for i in posts]):
        for i in posts:
            print('group from', i.get('from'))
        return False, "Все посты должны быть из одной группы"

    if from_info['is_closed']:
        return False, "Принимаются только открытые группы"

    if any([i.get('date') < start_time for i in posts]):
        return False, f"Все посты должны быть выложены не ранее {time.strftime('%d.%m.%y', time.localtime(start_time))}"

    posts_attachments = list()
    for post in posts:
        posts_attachments.append([i['type'] for i in post.get('attachments', [])])
    if any(['photo' not in i for i in posts_attachments]):
        return False, f"К каждому посту должно быть прикреплено изображение."

    else:
        group = db_api.Group.get_or_none(id=from_info['id'])
        if group:
            vk_link = f"@club{group.id} ({group.name})"
            return False, f"Группа \"{vk_link}\" уже добавлена в базу бота."

    return True, ''


async def save_art(image_url, source, add_by, from_group):
    old_image = db_api.Art.get_or_none(url=image_url)
    if old_image:
        return old_image, False

    future_vk_id = vk.upload_image(image_url)
    new_image = db_api.Art.create(vk_id=await future_vk_id,
                                  url=image_url,
                                  source=source,
                                  add_by=add_by,
                                  from_group=from_group,
                                  add_time=time.time())
    return new_image, True


async def prepare_art(image_url, group_id, post_id):
    return {
        'gid': abs(group_id),
        'pid': post_id,
        'url': image_url,
        'art': await vk.upload_image(image_url),
    }

