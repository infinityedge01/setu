import asyncio
import re
import sys
import requests
import random
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aip import AipContentCensor
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api import logger
import os

def saveImg(url, imgname, imgfolderdir):
    print('Saving image' + url)
    r = requests.get(url)
    with open(os.path.join(imgfolderdir, imgname + '.' + r.headers['Content-Type'][6:]), 'wb') as f:
        f.write(r.content)

def downloadImg(url):
    r = requests.head(url).headers
    if 'Size' in r:
        print('Size: ' + r['Size'])
        return int(r['Size'])
    return 0

    
async def Check_Baidu(imgurl, imgname, imgfolderdir):
    imgContent = downloadImg(imgurl)
    if imgContent < 5e4 or imgContent > 1e7:
        return
    
    censor_APP_ID = '22842022'
    censor_API_KEY = 'SEBH4QACKkEpGX7NRr7f4tYY'
    censor_SECRET_KEY = '0oI6FfOHbCuWSFlbgIpnlsBUGkKfOgxt'
    censor_client = AipContentCensor(censor_APP_ID, censor_API_KEY, censor_SECRET_KEY)
    
    censor_result = censor_client.imageCensorUserDefined(imgurl)
    
    #print(censor_result)
    if 'data' in censor_result:
        s = ''
        for each in censor_result['data']:
            s = s + each['msg'] + str(each['probability']) + ' '
        
        logger.debug(s)
        for each in censor_result['data']:
            #print('type', each['type'], 'prob', each['probability'])
            if each['msg']=='存在卡通色情不合规' and each['probability']>0.25:
                logger.debug('卡通色情%.6f' % each['probability'])
                saveImg(imgurl, imgname, imgfolderdir)
                return 1
            elif each['msg']=='存在卡通女性性感不合规' and each['probability']>0.25:
                logger.debug('卡通女性性感%.6f' % each['probability'])
                saveImg(imgurl, imgname, imgfolderdir)
                return 1
            elif each['msg']=='存在卡通亲密行为不合规' and each['probability']>0.25:
                logger.debug('卡通亲密行为%.6f' % each['probability'])
                saveImg(imgurl, imgname, imgfolderdir)
                return 1
    return 0

