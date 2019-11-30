# NPUMD_URP_classs_schedule

![效果图](https://i.loli.net/2019/11/23/Zg76kDsXiWajOcz.png)

## 简介

根据西北工业大学明德学院 URP 教务系统的选课结果生成 ics 日历。

## 功能

OCR 识别教务系统验证码自动登录，抓取选课结果页面信息并生成包含课程信息的 ics 文件，可导入手机、电脑等日历应用中快捷查看课表。

## 安装

请在 Python3 环境下运行。

识别验证码需要 [Tesseract](https://github.com/tesseract-ocr/tesseract)

macOS 可使用 Homebrew 安装:

`brew install tesseract`

需要安装的模块：

`pip install requests pillow pytesseract bs4`

复制一份 `config.ini.example` 命名为 `config.ini` 并打开。

`startDate` 为本学期第一周周一的日期。

在 `username` 和 `password` 中填写教务系统的账号及密码。

`url` 为本校的教务系统地址，默认为「西北工业大学明德学院」的教务系统，理论上支持所有采用 `1.5_0` 版「URP 综合教务系统」的学校，但未经实验，如有需要请修改相关信息自行测试。

`time` 中的上课时间，如有变动可修改对应时间。

信息填写完成后运行脚本，即可在当前目录生成一个名为「课程表.ics」的文件，导入日历系统即可。
