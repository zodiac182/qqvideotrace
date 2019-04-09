#! /usr/bin/env python
# -*- coding:utf-8 -*-
import sys
import requests
from datetime import datetime
import os
from Tkinter import *
import ttk
import threading
import logging
import webbrowser
from tkinter.ttk import Treeview
from lxml import etree
import time
import json
import tkMessageBox

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

reload(sys)
sys.setdefaultencoding('utf-8')


DATA_PATH = 'data/'
CONF_PATH = 'config/'
CONF_FILE = 'config/setting.conf'

'''
L format：
{
    'u_id':
    'u_name':
    'url':
    v_data:[
        {
            'v_id':
            'url':
            'title':
            'update_time':
        }
    ]
}
'''
#
# url_list = ['http://v.qq.com/vplus/txylqfq',
#          'http://v.qq.com/vplus/0a160ae96b5781fc18616f9785799de9',
#          'http://v.qq.com/vplus/bba3e259e3b8e555f9bb462829b154a5']


def log_insert(str):
    log_text.insert(
        END,
        '%s %s\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), str))
    log_text.see(END)


class App(ttk.Frame):
    def __init__(self, parent=None, *args, **kwargs):
        self._running = threading.Event()
        self._stop = threading.Event()
        self._stop.clear()

        self.init_UI(parent)
        self.init()

    def init_UI(self, parent=None):
        ttk.Frame.__init__(self, parent)
        self.parent = parent

        '''
        ### Frame setting
        '''
        self.frame_l = Frame(self.parent)
        self.frame_l.grid(row=0, column=0, padx=1, pady=1, sticky='NSWE')

        self.frame_r = Frame(self.parent)
        self.frame_r.grid(row=0, column=1, padx=1, pady=1, sticky='NSWE')
        Grid.rowconfigure(self.frame_r, 0, weight=1)
        Grid.columnconfigure(self.frame_r, 0, weight=1)

        '''
        ### setting_panel
        '''
        self.setting_panel = ttk.LabelFrame(self.frame_l, text=u"设置")
        self.setting_panel.grid(column=0, row=0, padx=5, pady=0)

        self.add_btn = Button(
            self.setting_panel, text=u"添加",
            command=self.add_btn_click, bg='#2E8B57')
        self.add_btn.grid(row=0, column=2, padx=1, pady=5, sticky='NWSE')

        self.new_url = StringVar()
        self.entry_new_url = Entry(
            self.setting_panel, textvariable=self.new_url)
        self.entry_new_url.grid(row=0, column=0, pady=5, columnspan=2, sticky='NWSE')

        Label(self.setting_panel, text=u'刷新频率(秒)：').grid(
            row=1, column=0, padx=0, pady=5, sticky='NWSE')

        self.set_btn = Button(
            self.setting_panel, text=u"设置",
            command=self.set_btn_click, bg='#2E8B57')
        self.set_btn.grid(row=1, column=2, pady=5, sticky='NWSE')

        self.refresh_delay = StringVar()
        self.entry_refresh_delay = Entry(
            self.setting_panel, textvariable=self.refresh_delay)
        self.entry_refresh_delay.grid(row=1, column=1, pady=5, sticky='NWSE')
        self.refresh_delay.set('60')

        '''
        ### control_panel
        '''
        self.control_panel = ttk.LabelFrame(self.frame_l, text=u"操作")
        self.control_panel.grid(column=0, row=1, padx=5, pady=0, sticky='NWSE')
        Grid.columnconfigure(self.control_panel, 0, weight=1)

        self.displayed_msg = StringVar()
        self.displayed_msg.set(u'正在初始化...')
        self.label = Label(self.control_panel, textvariable=self.displayed_msg, bg='#AAAAAA')
        self.label.grid(row=0, column=0, padx=1, pady=5, rowspan=2, sticky='NWSE')

        self.start_btn = Button(
            self.control_panel, text=u"开始",
            command=self.start_btn_click, bg='#2E8B57')
        self.start_btn.grid(row=0, column=1, padx=1, pady=5, sticky='NWSE')

        self.stop_btn = Button(
            self.control_panel, text=u"停止",
            command=self.stop_btn_click, bg='#2E8B57')
        self.stop_btn.grid(row=1, column=1, padx=1, pady=5, sticky='NWSE')

        '''
        ### Treeview
        '''
        self.tree = Treeview(
            self.frame_r,
            columns=['c1', 'c2', 'c3'],
            displaycolumns=['c1', 'c2'],
            selectmode='browse',
        )

        #  设置每列宽度和对齐方式
        self.tree.column('#0', anchor='center', width=60)
        self.tree.column('c1', anchor='w')
        self.tree.column('c2', anchor='center', width=80)
        self.tree.column('c3', anchor='center')

        #  设置每列表头标题文本
        self.tree.heading('c1', text=u'视频名称')
        self.tree.heading('c2', text=u'发布时间')
        self.tree.heading('c3', text=u'url')

        self.tree.grid(row=0, column=0, sticky='NSWE')

        # ----vertical scrollbar------------
        self.vbar = ttk.Scrollbar(
            self.frame_r, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vbar.set)
        self.vbar.grid(row=0, column=1, sticky='NS')

        '''
        #  定义并绑定Treeview组件的鼠标单击事件
        '''
        menu = Menu(self.frame_r, tearoff=0)
        menu.add_command(label=u"删除选中行", command=self.delete)
        def treeviewDoubleClick(event):
            '''
            如果是根结点，打开个人主页
            如果是子节点，打开视频页面
            '''
            webbrowser.open(
                self.tree.item(self.tree.selection()[0], "values")[2])

            if self.tree.tag_has('unread', self.tree.selection()[0]):
                self.tree.item(
                    self.tree.selection()[0],
                    image=image_old,
                    tag=['root', 'read'])

        def treeviewOpen(event):
            '''
            如果是根结点，打开个人主页
            如果是子节点，打开视频页面
            '''
            if self.tree.tag_has('unread', self.tree.selection()[0]):
                self.tree.item(
                    self.tree.selection()[0],
                    image=image_old,
                    tag=['root', 'read']
                )

        def treeviewPopupmenu(event):
            menu.post(event.x_root, event.y_root)

        self.tree.bind('<Double-1>', treeviewDoubleClick)
        self.tree.bind('<<TreeviewOpen>>', treeviewOpen)
        self.tree.bind('<Button-3>', treeviewPopupmenu)


    def init(self):
        if not os.path.exists(DATA_PATH):
            os.makedirs(DATA_PATH)

        if not os.path.exists(CONF_PATH):
            os.makedirs(CONF_PATH)

        self.data_list = []
        files = os.listdir(DATA_PATH)
        for file in files:
            with open('%s%s' %(DATA_PATH, file), 'r') as f:
                data = json.load(f)
                self.new_watcher(json.dumps(data))

        if os.path.exists(CONF_FILE):
            with open(CONF_FILE, 'r') as f:
                try:
                    self.refresh_delay.set(json.load(f)['wait_time'])
                except:
                    pass

        self.p = threading.Thread(target=self.run)
        self.delay = int(self.refresh_delay.get())

        self.status_audit()

    def new_watcher(self, data):
        logging.info('new_watcher')
        logging.info(data)
        info = json.loads(data)
        try:
            self.tree.insert('', 'end',
                             info['u_id'],
                             text=info['u_name'],
                             image=image_old,
                             values=['', '', info['url']],
                             tag=['root', 'read'])
            self.data_list.append(info)
        except Exception, ex:
            logging.error(ex)

    def start_btn_click(self):
        if self.p.isAlive():
            tkMessageBox.showinfo(u"", u"程序运行中")
        else:
            self._running.set()
            self._stop.clear()
            if self.p.ident is not None:
                self.p = threading.Thread(target=self.run)
            self.p.setDaemon(True)
            self.p.start()
            self.p.join(1)


    def stop_btn_click(self):
        if self._running.isSet() and self.p.isAlive():
            self._running.clear()
            self._stop.set()

    def status_audit(self):
        aud_p = threading.Thread(target=self.status_check)
        aud_p.setDaemon(True)
        aud_p.start()
        aud_p.join(1)

    def status_check(self):
        while True:
            try:
                if self.p.isAlive():
                    self.displayed_msg.set(u'程序运行中...\n当前间隔时间(s):%s' % self.delay)
                else:
                    self.displayed_msg.set(u'程序已停止。\n请点击开始按钮启动程序。')
            except Exception:
                self.displayed_msg.set(u'初始化完成。等待开始')

            time.sleep(1)

    def crawling(self, data):
        logging.info('crawling...')
        p_info = json.loads(data)
        # p_info = {'url': url}
        # p_info['u_id'] = re.match(
        #     r'http://v.qq.com/vplus/(.*)$', url).group(1)

        logging.info(p_info)

        r = requests.get(p_info['url'])

        html_tree = etree.HTML(unicode(r.content))

        logging.info(r.status_code)
        if r.status_code != requests.codes.OK:
            return

        user_name = html_tree.xpath(
            '//*//span[@id="userInfoNick"]/text()')[0]

        p_info['u_name'] = user_name

        if self.tree.exists(p_info['u_id']):
            pass
        else:
            self.tree.insert('', 'end',
                             p_info['u_id'],
                             text=user_name,
                             image=image_new,
                             values=[
                                 '', '', p_info['url']],
                             tag=['root', 'unread'])

        video_list = html_tree.xpath(
            '//*[@id="mod_video_listcont"]/li[@class="list_item"]')

        '''
        如果存在没抓取的视频，证明有更新，则重建二级列表，否则更新视频发布时间
        '''
        latest_v_id = re.match(r'https://v.qq.com/x/page/(.*)\.html',
                               video_list[0].xpath('./strong/a/@href')[0]).group(1)

        if self.tree.exists(latest_v_id):
            for video in video_list:
                v_id = re.match(r'https://v.qq.com/x/page/(.*)\.html',
                                video.xpath('./strong/a/@href')[0]).group(1)

                if self.tree.exists(v_id):
                    if self.tree.item(v_id, 'values')[1] != \
                            video.xpath('./div/span[@class="figure_info_time"]/text()')[0]:
                        item = [video.xpath('./strong/a/text()')[0],
                                video.xpath('./div/span[@class="figure_info_time"]/text()')[0],
                                video.xpath('./strong/a/@href')[0]]
                        self.tree.item(v_id, values=item)
        else:
            '''清除现存二级列表'''
            x = self.tree.get_children(p_info['u_id'])
            for item in x:
                self.tree.delete(item)

            '''更新未读标识'''
            self.tree.item(
                p_info['u_id'],
                image=image_new,
                tag=['root', 'unread']
            )

            # video_info_list = []
            '''抓取视频列表'''
            for video in video_list:
                v_id = re.match(r'https://v.qq.com/x/page/(.*)\.html',
                                video.xpath('./strong/a/@href')[0]).group(1)
                video_info = {'v_id': v_id,
                              'url': video.xpath('./strong/a/@href')[0],
                              'title': video.xpath('./strong/a/text()')[0],
                              'update_time': video.xpath('./div/span[@class="figure_info_time"]/text()')[0]}
                # video_info_list.append(video_info)

                item = [video_info['title'],
                        video_info['update_time'],
                        video_info['url']]
                self.tree.insert(
                    p_info['u_id'], 'end', video_info['v_id'], values=item, tag='child')

    def run(self):
        logging.info(self.data_list)
        while(self._running.isSet()):
            for data in self.data_list:
                self.crawling(json.dumps(data))
            self._stop.wait(self.delay)


    def set_btn_click(self):
        try:
            self.delay = int(self.refresh_delay.get())
            tkMessageBox.showinfo(u"完成", u"设置完成，新的间隔时间将于重新开始程序之后生效")
            with open(CONF_FILE, 'w+') as f:
                tmpjson={'wait_time': self.delay}
                json.dump(tmpjson,f)
        except Exception,ex:
            tkMessageBox.showerror(u"错误", u"格式错误，必须为数字" + ex)

    def add_btn_click(self):
        new_url = self.new_url.get().strip()
        config_j2 = {'u_id': ''}
        if re.match(r'http://v.qq.com/vplus/(.*)$', new_url):
            u_id = re.match(r'http://v.qq.com/vplus/(.*)$', new_url).group(1)
            if os.path.exists('%s%s.json' % (DATA_PATH, u_id)):
                tkMessageBox.showerror(u'Error', u'已存在')
            else:
                config_j2['u_id'] = u_id
                config_j2['url'] = new_url

                r = requests.get(new_url)
                html_tree = etree.HTML(unicode(r.content))

                if r.status_code != requests.codes.OK:
                    tkMessageBox.showerror(u'Error', u'无法打开网页\n%s' % new_url)
                    return

                config_j2['u_name'] = html_tree.xpath(
                    '//*//span[@id="userInfoNick"]/text()')[0]

                #  写文件
                with open('%s%s.json' % (DATA_PATH, u_id), 'w+') as f:
                    json.dump(config_j2, f)

                self.new_watcher(json.dumps(config_j2))
        else:
            tkMessageBox.showerror(u'Error', u'网址格式错误')

        self.new_url.set('')

    def delete(self):
    	print len(self.tree.selection()) > 0
        if len(self.tree.selection()) > 0:
            u_id = self.tree.selection()[0]
            if self.tree.tag_has('root', u_id):
                os.remove('%s%s.json' % (DATA_PATH, u_id))
                for data in self.data_list:
                    if data['u_id'] == u_id:
                        self.data_list.remove(data)
                        self.tree.delete(u_id)
                pass
            else:
                tkMessageBox.showerror('Error', u'请选中用户之后再进行删除')


if __name__ == '__main__':
    root = Tk()

    global image_new
    image_new = PhotoImage(file="pic/new.gif")
    global image_old
    image_old = PhotoImage(file="pic/old.gif")

    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.geometry("%dx%d" % (w, h))
    root.title(u'QQ视频追踪')
    root.rowconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)

    app = App(parent=root)

    root.mainloop()
