"""Windows sponge desktop pet. Python 3 + tkinter; no pip dependencies."""
import ctypes
import json
import os
from pathlib import Path
import queue
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from behavior import Behavior
from tray import Tray
from motion_config import read_motion_config

BG = '#ff00ff'
BASE = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'SpongePet' / 'settings.json'


class Pet:
    def __init__(self):
        if sys.platform != 'win32':
            raise SystemExit('Please run this desktop pet on Windows, not in WSL.')
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.root = tk.Tk()
        self.root.title('海绵桌面宠物')
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes('-transparentcolor',BG)
        self.topmost = True
        self.root.attributes('-topmost',True)
        self.canvas = tk.Canvas(self.root,bg=BG,highlightthickness=0)
        self.canvas.pack()
        self.model = Behavior(time.monotonic())
        self.scale = 100
        self.transparency = 0
        self.hidden = False
        self.drag = None
        self.dragged = False
        self.settings = None
        self.last_frame = None
        self.load_config()
        motion=read_motion_config(BASE/'pet.ini')
        self.model.animation_fps=motion['walk_fps']
        self.model.eat_fps=motion['eat_fps']
        self.model.walk_speed=motion['walk_speed']
        self.model.follow_speed=motion['follow_speed']
        self.base_frames = {}
        for name,count in [('front',1),('left',4),('right',4),('eat',6)]:
            self.base_frames[name] = [tk.PhotoImage(file=str(BASE/'assets'/(f'{name}.png' if name=='front' else f'{name}_{i}.png'))) for i in range(count)]
        self.sprite_item = self.canvas.create_image(0,0,anchor='s',tags='character')
        self.resize(self.scale)
        self.refresh_bounds()
        l,t,r,b = self.bounds
        self.model.x = (l+r-self.w)/2
        self.model.y = b-self.h-20
        self.model.tx,self.model.ty = self.model.x,self.model.y
        self.root.protocol('WM_DELETE_WINDOW',self.quit)
        self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<B1-Motion>',self.motion)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Button-3>',self.right_click)
        self.root.bind('<Escape>',lambda e:self.quit())
        self.last = time.monotonic()
        self.next_bounds = 0
        self.tray = Tray(BASE/'assets'/'sponge.ico')
        self.root.after(100,self.poll_tray)
        self.tick()
        self.root.mainloop()

    def load_config(self):
        try:
            data = json.loads(CONFIG.read_text(encoding='utf-8'))
            self.scale = int(data.get('scale',100))
            if self.scale not in (50,75,100,125,150,175,200):self.scale=100
            self.transparency = max(0,min(100,float(data.get('transparency',0))))
            self.root.attributes('-alpha',1-self.transparency/100)
            self.topmost = bool(data.get('topmost',True))
            self.root.attributes('-topmost',self.topmost)
        except (OSError,ValueError,TypeError,AttributeError):
            pass

    def save_config(self):
        data = dict(scale=self.scale,topmost=self.topmost,transparency=self.transparency)
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True)
            CONFIG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError as e:
            messagebox.showwarning('设置未保存',str(e),parent=self.settings or self.root)

    def resize(self,percent):
        self.scale = int(percent)
        numerator = self.scale//25
        self.frames = {name:[im.zoom(numerator).subsample(4) for im in images] for name,images in self.base_frames.items()}
        self.w = round(180*self.scale/100)
        self.h = round(210*self.scale/100)
        self.canvas.configure(width=self.w,height=self.h)
        self.canvas.coords(self.sprite_item,self.w//2,self.h-round(8*self.scale/100))
        self.last_frame = None
        self.canvas.itemconfigure(self.sprite_item,image=self.frames['front'][0])

    def refresh_bounds(self):
        from ctypes import wintypes
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030,0,ctypes.byref(rect),0):
            self.bounds = rect.left,rect.top,rect.right,rect.bottom
        else:
            self.bounds = 0,0,self.root.winfo_screenwidth(),self.root.winfo_screenheight()

    def press(self,e):
        self.model.interact(time.monotonic())
        self.drag = e.x_root,e.y_root,self.model.x,self.model.y
        self.dragged = False

    def motion(self,e):
        if self.drag:
            px,py,x,y = self.drag
            if abs(e.x_root-px)+abs(e.y_root-py)>5:self.dragged=True
            if self.dragged:
                self.model.x,self.model.y=x+e.x_root-px,y+e.y_root-py

    def release(self,e):
        now = time.monotonic()
        if self.drag and not self.dragged:
            self.model.toggle_follow(now)
        self.drag = None
        self.model.rest(now)

    def poll_tray(self):
        try:
            while True:
                event,detail = self.tray.events.get_nowait()
                if event=='settings':self.open_settings()
                elif event=='error':
                    self.open_settings()
                    messagebox.showwarning('托盘图标未能创建',detail,parent=self.settings)
        except queue.Empty:
            pass
        self.root.after(100,self.poll_tray)

    def open_settings(self):
        # Opening settings counts as interaction.
        self.model.interact(time.monotonic())
        if self.settings and self.settings.winfo_exists():
            self.settings.deiconify();self.settings.lift();self.settings.focus_force();return
        win = self.settings = tk.Toplevel(self.root)
        win.title('海绵宠物设置')
        win.resizable(False,False)
        win.attributes('-topmost',True)
        win.attributes('-alpha',1.0)
        win.protocol('WM_DELETE_WINDOW',lambda:self.close_settings())
        pane = ttk.Frame(win,padding=18);pane.pack(fill='both',expand=True)
        ttk.Label(pane,text='海绵桌面宠物',font=('Microsoft YaHei UI',15,'bold')).pack(anchor='w')
        ttk.Label(pane,text='点击宠物切换跟随；拖动可移动位置。').pack(anchor='w',pady=(4,12))
        self.vars = {}
        self.value_labels = {}
        for name,title,value in [('topmost','保持置顶',self.topmost)]:
            v=tk.BooleanVar(value=value);self.vars[name]=v
            ttk.Checkbutton(pane,text=title,variable=v,command=self.apply_settings).pack(anchor='w',pady=3)
        row=ttk.Frame(pane);row.pack(fill='x',pady=(12,3))
        ttk.Label(row,text='宠物大小').pack(side='left')
        self.vars['scale']=tk.StringVar(value=str(self.scale))
        box=ttk.Combobox(row,textvariable=self.vars['scale'],values=['50','75','100','125','150','175','200'],state='readonly',width=8)
        box.pack(side='right');box.bind('<<ComboboxSelected>>',lambda e:self.apply_settings())
        row=ttk.Frame(pane);row.pack(fill='x',pady=(6,3))
        self.vars['transparency']=tk.DoubleVar(value=self.transparency)
        self.transparency_label=ttk.Label(row,text=f'透明度：{round(self.transparency)}%（0% 为不透明）',width=34)
        self.transparency_label.pack(side='left')
        ttk.Scale(row,from_=0,to=100,variable=self.vars['transparency'],command=lambda value:self.apply_settings(),length=170).pack(side='right')
        ttk.Separator(pane).pack(fill='x',pady=12)
        actions=ttk.Frame(pane);actions.pack(fill='x')
        self.feed_button=ttk.Button(actions,text='喂蟹黄堡',command=self.feed)
        self.feed_button.pack(side='left',padx=(0,6))
        ttk.Button(actions,text='暂停 / 继续',command=self.pause).pack(side='left',padx=3)
        actions2=ttk.Frame(pane);actions2.pack(fill='x',pady=(8,0))
        ttk.Button(actions2,text='隐藏 / 显示宠物',command=self.hide_toggle).pack(side='left')
        ttk.Button(actions2,text='恢复默认',command=self.defaults).pack(side='left',padx=6)
        ttk.Button(actions2,text='退出宠物',command=self.quit).pack(side='right')
        self.status=tk.StringVar(value='')
        ttk.Label(pane,textvariable=self.status).pack(anchor='w',pady=(10,0))
        self.update_feed_button()
        win.update_idletasks()
        mx,my=self.root.winfo_pointerxy()
        width,height=win.winfo_width(),win.winfo_height()
        l,t,r,b=self.bounds
        win.geometry(f'+{max(l,min(mx-width//2,r-width))}+{max(t,min(my-height,b-height))}')
        win.lift();win.focus_force()

    def update_feed_button(self):
        if self.settings and self.settings.winfo_exists() and hasattr(self,'feed_button'):
            active=not self.hidden
            self.feed_button.configure(state='normal' if active else 'disabled')
            self.status.set('右键海绵即可吃蟹黄堡。动画与速度请修改 pet.ini。')

    def apply_settings(self):
        if not hasattr(self,'vars'):return
        self.topmost=self.vars['topmost'].get()
        self.root.attributes('-topmost',self.topmost)
        self.transparency=self.vars['transparency'].get()
        self.root.attributes('-alpha',1-self.transparency/100)
        self.transparency_label.configure(text=f'透明度：{round(self.transparency)}%（0% 为不透明）')
        if self.vars['scale'].get() and int(self.vars['scale'].get())!=self.scale:
            self.resize(int(self.vars['scale'].get()))
        for key,(label,title) in self.value_labels.items():
            label.configure(text=f'{title}：{round(self.vars[key].get())}')
        self.update_feed_button()

    def close_settings(self):
        self.save_config()
        self.settings.destroy();self.settings=None

    def right_click(self,e):
        self.feed()

    def feed(self):
        if not self.hidden and self.model.feed(time.monotonic()):
            self.update_feed_button()

    def pause(self):
        self.model.interact(time.monotonic())
        self.model.paused=not self.model.paused

    def hide_toggle(self):
        self.hidden=not self.hidden
        if self.hidden:self.root.withdraw()
        else:self.root.deiconify();self.root.attributes('-topmost',self.topmost)
        self.update_feed_button()

    def defaults(self):
        defaults=dict(topmost=True,transparency=0,scale='100')
        for key,value in defaults.items():self.vars[key].set(value)
        self.apply_settings()

    def tick(self):
        now=time.monotonic();dt=min(now-self.last,0.05);self.last=now
        if now>=self.next_bounds:
            self.refresh_bounds();self.next_bounds=now+1
        moving=self.model.update(now,dt,self.bounds,(self.w,self.h),self.root.winfo_pointerxy(),dragging=bool(self.drag) or self.hidden or bool(self.settings))
        self.root.geometry(f'{self.w}x{self.h}{round(self.model.x):+d}{round(self.model.y):+d}')
        key=self.model.frame(now,moving)
        if self.drag and self.model.action!='eat':key=('front',0)
        base_key = key
        if base_key!=self.last_frame:
            self.canvas.itemconfigure(self.sprite_item,image=self.frames[base_key[0]][base_key[1]])
            self.last_frame=base_key
        self.update_feed_button()
        self.root.after(33,self.tick)

    def quit(self):
        self.save_config()
        self.tray.close()
        self.root.destroy()


if __name__=='__main__':
    Pet()
