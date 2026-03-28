
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from aiocqhttp.message import Message, MessageSegment
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message import components 
from astrbot.api.event import MessageChain
import astrbot.api.message_components as Comp
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from .setu_censor import Check_Baidu
import random
import os
import asyncio
import requests
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from .database import *

@register("setu", "infedg", "一个简单的涩图插件", "0.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self.contrib_count = 0
        self.setu_count = 0
        db_path = get_astrbot_data_path()
        self.db = Database(db_path)
        self.setu_path = os.path.join(db_path, 'setu')
        if not os.path.exists(self.setu_path):
            os.makedirs(self.setu_path)
        self.setu_list = os.listdir(self.setu_path)
        self.last_visit = {}
        self.update_contrib_count()
        self.update_setu_count()
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        trigger = CronTrigger(second=10)
        self.scheduler.add_job(
            func=self._call_update,  # 要添加任务的函数，不要带参数
            trigger=trigger,  # 触发器
            kwargs=None,  # 函数的参数列表，注意：只有一个值时，不能省略末尾的逗号
            misfire_grace_time=1,  # 允许的误差时间，建议不要省略
        )

    def update_contrib_count(self):
        time = datetime.datetime.now().hour * 6 + datetime.datetime.now().minute // 10
        self.db.update_total_contrib(time, self.contrib_count)
        self.contrib_count = 0

    def update_setu_count(self):
        time = datetime.datetime.now().hour * 6 + datetime.datetime.now().minute // 10
        self.db.update_total_setu(time, self.setu_count)
        setu_count = 0

    async def _call_update(self):
        logger.debug('call_update')
        self.update_setu_count()
        await asyncio.sleep(10)
        self.update_contrib_count()

    async def can_get_a_setu(self, user_id: int) -> bool:
        current_time = datetime.datetime.now()
        delta = datetime.timedelta(minutes=1)
        
        if user_id in self.last_visit:
            if self.last_visit[user_id] + delta > current_time:
                return False
        self.last_visit[user_id] = current_time + delta
        return True
    
    async def get_a_setu(self) -> MessageSegment:
        if len(self.setu_list) < 100:
            url = 'https://api.lolicon.app/setu/v2?size=original&size=regular'
            setu_url = None
            for i in range(3):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
                    }
                    data = requests.get(url, headers=headers).json()
                    logger.debug(data)
                    setu_url = data['data'][0]['urls']['regular']
                    break
                except:
                    pass
            assert(setu_url)
            return MessageSegment.image(setu_url)
        setu_file = random.choice(self.setu_list)
        cur_setu_path = os.path.join(self.setu_path, setu_file)
        logger.debug(cur_setu_path)
        return MessageSegment.image("file://" + cur_setu_path)
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def process_image_message(self, event: AstrMessageEvent):
        if event.get_platform_name() == "aiocqhttp":
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot # 得到 client
            user_id = int(event.message_obj.sender.user_id)
            if event.message_obj.message_str == '涩图' or event.message_obj.message_str == '色图':
                Flag = await self.can_get_a_setu(user_id)
                if not Flag:
                    await client.send_group_msg(group_id=int(event.get_group_id()), message= MessageSegment.text('你看太多涩图了'))
                else:
                    self.db.update_setu(user_id)
                    self.setu_count += 1
                    msg1 = await self.get_a_setu()
                    logger.debug(str(msg1))
                    msg_data = await client.send_group_msg(group_id=int(event.get_group_id()), message= msg1)
                    logger.debug(str(msg_data['message_id']))
                    # 制作一个“20秒钟后”触发器
                    delta = datetime.timedelta(seconds=20)
                    trigger = DateTrigger(
                        run_date=datetime.datetime.now() + delta
                    )
                    logger.debug('撤回消息' + event.message_obj.self_id)
                    self.scheduler.add_job(
                        func=event.bot.delete_msg,  # 要添加任务的函数，不要带参数
                        trigger=trigger,  # 触发器
                        kwargs={'message_id':msg_data['message_id'], 'self_id':int(event.message_obj.self_id)},  # 函数的参数列表，注意：只有一个值时，不能省略末尾的逗号
                        misfire_grace_time=1,  # 允许的误差时间，建议不要省略
                    )
            for i, x in enumerate(event.message_obj.message):
                if x.type == components.ComponentType.Image:
                    assert(type(x) == components.Image)
                    url = x.url
                    if url == None: continue
                    name = url[-41:-9]
                    file_size = int(event.message_obj.raw_message.message[i]['data']['file_size'])
                    if file_size < 5e4 or file_size > 1e7:
                        continue
                    t = await Check_Baidu(url, name, self.setu_path)
                    if t == 1:
                        self.contrib_count += 1
                        self.db.update_contrib(user_id)
                        await client.send_group_msg(group_id=int(event.get_group_id()), message= MessageSegment.text('涩图！'))
                        rnd = random.randint(1,5)
                        if rnd == 1:
                            await client.send_group_msg(group_id=int(event.get_group_id()), message= MessageSegment.text('只要涩图存入库中「涩图！」一响，你的灵魂立刻从炼狱直升天堂'))
                        return

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
