import requests
import random
from PIL import Image
import pytesseract
from bs4 import BeautifulSoup
import os
import re
import datetime
import configparser
from io import BytesIO

config = configparser.ConfigParser()
config.read('config.ini')


# 教务系统地址
url = config['URP'].get('url')

# 教务系统账号密码
username = config['URP'].get('username')
password = config['URP'].get('password')

# 第一周周一日期
startYear = config['startDate'].getint('year')
startMonth = config['startDate'].getint('month')
startDay = config['startDate'].getint('day')

beginDate = datetime.date(startYear, startMonth, startDay)


startTime = [None]
startTime.extend(config['time'].get('startTime').replace(' ', '').split(','))

endTime = [None]
endTime.extend(config['time'].get('endTime').replace(' ', '').split(','))

weekName = [None]
weekName.extend(config['time'].get('weekName').replace(' ', '').split(','))

VCALENDAR = '''BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:%(username)s 课程表
X-WR-TIMEZONE:Asia/Shanghai
X-WR-CALDESC:%(username)s 课程表
BEGIN:VTIMEZONE
TZID:Asia/Shanghai
X-LIC-LOCATION:Asia/Shanghai
BEGIN:STANDARD
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
''' % {'username': username}


def get_captcha(session):
    for i in range(10):
        captcha_url = url+'validateCodeAction.do'

        captcha_data = {
            'random': random.random()
        }

        response = session.get(captcha_url, params=captcha_data)

        im = Image.open(BytesIO(response.content))
        w, h = im.size
        im = im.resize((w*2, h*2))
        gray = im.convert('L')  # 灰度处理

        threshold = 150
        table = []
        for i in range(256):
            if i < threshold:
                table.append(0)
            else:
                table.append(1)
        out = gray.point(table, '1')

        code = pytesseract.image_to_string(out)

        code = filter(str.isalnum, code)
        code = ''.join(list(code))

        if len(code) == 4:
            break

    return code


loginSuccess = False
session = requests.session()


for _ in range(5):
    captcha = get_captcha(session)

    login_url = url+'loginAction.do'

    post_data = {
        'zjh': username,
        'mm': password,
        'v_yzm': captcha
    }

    login_res = session.post(login_url, data=post_data)
    outline_url = url+'outlineAction.do'
    outline_res = session.get(outline_url)

    if(outline_res.status_code == 200):
        loginSuccess = True
        break


if loginSuccess:
    table_url = url+'xkAction.do'

    data = {
        'actionType': '6'
    }

    tablePage = session.get(table_url, params=data).content.decode("gb2312")

    soup = BeautifulSoup(tablePage, 'lxml')

    classes = soup.find_all('tr', class_='odd')

    file = open('课程表.ics', 'w')
    file.write(VCALENDAR)
    for Class in classes:
        VEVENT = ''

        Class = Class.find_all('td')
        if len(Class) == 18:
            className = Class[2].text.strip()  # 课程名
            classWeekTimes = Class[11].text.strip()  # 周次
            classWeek = Class[12].text.strip()  # 星期
            classSession = Class[13].text.strip()  # 节次
            classAmount = Class[14].text.strip()  # 节数
            classBuilding = Class[16].text.strip()  # 教学楼
            classRoom = Class[17].text.strip()  # 教室
        elif len(Class) == 7:
            classWeekTimes = Class[0].text.strip()  # 周次
            classWeek = Class[1].text.strip()  # 星期
            classSession = Class[2].text.strip()  # 节次
            classAmount = Class[3].text.strip()  # 节数
            classBuilding = Class[5].text.strip()  # 教学楼
            classRoom = Class[6].text.strip()  # 教室

        #print(className, classWeekTimes, classWeek, classSession, classAmount, classBuilding, classRoom)

        VEVENT += 'BEGIN:VEVENT\n'
        # 周次
        WeekTimes = re.findall(r"\d+\.?\d*", classWeekTimes)
        # 开始周
        delta = datetime.timedelta(weeks=int(WeekTimes[0])-1)
        # 开始星期
        delta += datetime.timedelta(days=int(classWeek)-1)
        classStartTime = beginDate+delta
        # 开始日期
        classStartDate = beginDate+delta
        # 开始时间
        classStartTime = datetime.datetime.strptime(
            startTime[int(classSession)], '%H:%M').time()
        # 结束时间
        classEndTime = datetime.datetime.strptime(
            endTime[int(classSession)+int(classAmount)-1], '%H:%M').time()
        # 最终开始时间
        classStartDateTime = datetime.datetime.combine(
            classStartDate, classStartTime)
        # 最终结束时间
        classEndDateTime = datetime.datetime.combine(
            classStartDate, classEndTime)
        # 写入开始时间
        VEVENT += 'DTSTART;TZID=Asia/Shanghai:{classStartDateTime}\n'.format(classStartDateTime=classStartDateTime.strftime(
            '%Y%m%dT%H%M%S'))
        # 写入结束时间
        VEVENT += 'DTEND;TZID=Asia/Shanghai:{classEndDateTime}\n'.format(classEndDateTime=classEndDateTime.strftime(
            '%Y%m%dT%H%M%S'))

        # 设置循环
        if '-'in classWeekTimes:
            VEVENT += 'RRULE:FREQ=WEEKLY;WKST=MO;COUNT={count};BYDAY={byday}\n'.format(count=str(
                int(WeekTimes[1])-int(WeekTimes[0])+1), byday=weekName[int(classWeek)])
        else:
            interval = int(WeekTimes[1])-int(WeekTimes[0])
            VEVENT += 'RRULE:FREQ=WEEKLY;WKST=MO;COUNT={count};INTERVAL={interval};BYDAY={byday}\n'.format(
                count=str(len(WeekTimes)), interval=str(interval), byday=weekName[int(classWeek)])

        # 地点
        VEVENT += ('LOCATION:'+classBuilding+classRoom+'\n')
        # 名称
        VEVENT += ('SUMMARY:'+className+'\n')
        VEVENT += 'END:VEVENT\n'
        file.write(VEVENT)
    file.write('END:VCALENDAR')
    file.close()

else:
    print('登录失败')
