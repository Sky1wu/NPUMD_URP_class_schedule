import requests
import random
from PIL import Image
import pytesseract
from bs4 import BeautifulSoup
import os
import re
import datetime

# 教务系统地址
url = 'http://urp.npumd.cn/'

# 教务系统账号密码
username = ''
password = ''

# 第一周周一日期
beginDate = datetime.date(2019, 9, 9)

'''
上课时间：
01: 08:30 - 09:15
02: 09:25 - 10:10
03: 10:25 - 11:10
04: 11:20 - 12:05
05: 14:00 - 14:45
06: 14:55 - 15:40
07: 15:50 - 16:35
08: 16:45 - 17:30
09: 19:00 - 19:45
10: 19:55 - 20:40
11: 20:50 - 21:35

startTime 和 endTime 与此时间表对应
'''

startTime = (None, '083000', '092500', '102500',
             '112000', '140000', '145500', '155000', '164500', '190000', '195500', '205000')

endTime = (None, '091500', '101000', '111000', '120500',
           '144500', '154000', '163500', '173000', '194500', '204000', '213500')

weekName = (None, 'MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')

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

        file = open('captcha.png', 'wb')
        file.write(response.content)
        file.close()

        im = Image.open('captcha.png')
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
        out.save('captcha_thresholded.png')

        th = Image.open('captcha_thresholded.png')
        code = pytesseract.image_to_string(th)

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

os.remove('captcha.png')
os.remove('captcha_thresholded.png')

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
        WeekTimes = re.findall(r"\d+\.?\d*", classWeekTimes)
        delta = datetime.timedelta(weeks=int(WeekTimes[0])-1)
        delta += datetime.timedelta(days=int(classWeek)-1)
        classStartTime = beginDate+delta
        VEVENT += ('DTSTART;TZID=Asia/Shanghai:' +
                   classStartTime.strftime("%Y%m%dT")+startTime[int(classSession)]+'\n')
        VEVENT += ('DTEND;TZID=Asia/Shanghai:' +
                   classStartTime.strftime("%Y%m%dT")+endTime[int(classSession)+int(classAmount)-1]+'\n')
        if '-'in classWeekTimes:
            VEVENT += ('RRULE:FREQ=WEEKLY;WKST=MO;COUNT=' +
                       str(int(WeekTimes[1])-int(WeekTimes[0])+1)+';BYDAY='+weekName[int(classWeek)]+'\n')
        else:
            interval = int(WeekTimes[1])-int(WeekTimes[0])
            VEVENT += ('RRULE:FREQ=WEEKLY;WKST=MO;COUNT=' +
                       str(len(WeekTimes))+';INTERVAL='+str(interval)+';BYDAY='+weekName[int(classWeek)]+'\n')
        VEVENT += ('LOCATION:'+classBuilding+classRoom+'\n')
        VEVENT += ('SUMMARY:'+className+'\n')
        VEVENT += 'END:VEVENT\n'
        file.write(VEVENT)
    file.write('END:VCALENDAR')
    file.close()

else:
    print('登录失败')
