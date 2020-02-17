import logging
import json
import asyncio
from main import vk

class Button:
    def __init__(self, label, payload, color='default'):
        self.label = label
        self.payload = payload
        self.color = color


class Keyboard:
    def __init__(self, default_payload=None, buttons=None, inline=False, one_time=False):
        self.buttons = buttons if buttons else [[]]
        self.one_time = one_time if not inline else False
        self.inline = inline
        self.default_payload = default_payload if default_payload else []

    def add_button(self, label, payload, color='default', row=-1):
        new_payload = self.default_payload + [payload] if payload else self.default_payload
        new_button = Button(label, new_payload, color)
        if row >= len(self.buttons):
            self.buttons.extend([[] for _ in range(row - len(self.buttons) + 1)])
        self.buttons[row].append(new_button)

    def navigation_buttons(self):
        self.buttons.extend([[] for _ in range(10 - len(self.buttons) + 1)])
        if len(self.default_payload) > 1:
            self.buttons[10] = [Button('назад', self.default_payload[:-1])]
        self.buttons[10].append(Button('домой', self.default_payload + [{'mid': 'main'}]))

    def get_vk_keyboard(self):
        buttons = []
        for button_row in self.buttons:
            if button_row:
                buttons.append([])
                for button in button_row:
                    if self.inline and len(buttons) >= 3:
                        buttons.append([])
                    elif not self.inline and len(buttons) >= 4:
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
    def __init__(self, peer_id, text, default_payload=None, attachments=None, keyboard=None):
        self.peer_id = peer_id
        self.text = text
        self.attachments = attachments if attachments else []
        self.keyboard = keyboard if keyboard else Keyboard(default_payload=default_payload)

    def convert_to_vk(self):
        return {
            'peer_id': self.peer_id,
            'message': self.text,
            'attachment': ','.join(self.attachments),
            'keyboard': self.keyboard.get_vk_keyboard()
        }


class Functions:
    async def no_menu(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Ошибка доступа",
            default_payload=msg.payload
        )
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def main(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Сейчас вы в главном меню",
            default_payload=msg.payload
        )
        bot_message.keyboard.add_button('второе меню', {'mid': 'menu_2'})
        bot_message.keyboard.add_button('третье меню', {'mid': 'menu_3'})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def menu_2(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Теперь вы во втором меню\n"
                 "Напишите какой-нибудь текст и отправьте его.\n"
                 "Когда закончите ввод текста нажмите кнопку сохранить.",
            default_payload=msg.payload
        )
        bot_message.keyboard.add_button('сохранить текст', {'mid': 'save_text'})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def save_text(self, msg):
        user_text = '\n'.join([m.text for m in msg.unprocessed_messages])
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Ваш текст: \n\n" + user_text,
            default_payload=msg.payload[:-1]
        )
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def menu_3(self, msg):
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Теперь вы в третьем меню\n"
                 "Прекрепите к сообщению изображения и отправьте его.\n"
                 "Когда закончите отправку изображений нажмите кнопку сохранить.\n"
                 "В сумме должно быть не более 10 изображений.",
            default_payload=msg.payload
        )
        bot_message.keyboard.add_button('сохранить изображения', {'mid': 'save_img'})
        bot_message.keyboard.navigation_buttons()
        return bot_message

    async def save_img(self, msg):
        urls = list()
        for user_message in msg.unprocessed_messages:
            for attachment in user_message.attachments:
                if attachment['type'] == 'photo':
                    photo_sizes = attachment['photo']['sizes']
                    photo_sizes.sort(key=lambda x: x['height'], reverse=True)
                    urls.append(photo_sizes[0]['url'])
        # print('urls', urls)
        tasks = [asyncio.create_task(vk.upload_image(url)) for url in urls[:10]]
        user_images = await asyncio.gather(*tasks)
        bot_message = BotMessage(
            peer_id=msg.peer_id,
            text="Ваши изображения:",
            default_payload=msg.payload[:-1],
            attachments=user_images
        )
        bot_message.keyboard.navigation_buttons()

        return bot_message



