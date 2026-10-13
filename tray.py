"""Native Windows notification-area icon. All GUI actions go through a queue."""
import ctypes as C
from ctypes import wintypes as T
import threading
import queue


class Tray:
    def __init__(self, icon_path):
        self.events = queue.Queue()
        self.icon_path = str(icon_path)
        self.hwnd = None
        self.stopping = threading.Event()
        self.user = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def close(self):
        self.stopping.set()
        if self.hwnd and self.user:
            self.user.PostMessageW(self.hwnd, 0x0010, 0, 0)

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.events.put(('error', str(e)))

    def _run(self):
        u = C.WinDLL('user32', use_last_error=True)
        self.user = u
        u.PostMessageW.argtypes = [T.HWND,T.UINT,T.WPARAM,T.LPARAM]
        u.PostMessageW.restype = T.BOOL
        k = C.WinDLL('kernel32', use_last_error=True)
        shell = C.WinDLL('shell32', use_last_error=True)
        LRESULT = C.c_ssize_t
        WNDPROC = C.WINFUNCTYPE(LRESULT, T.HWND, T.UINT, T.WPARAM, T.LPARAM)
        class WNDCLASS(C.Structure):
            _fields_ = [('style', T.UINT), ('lpfnWndProc', WNDPROC),
                        ('cbClsExtra', C.c_int), ('cbWndExtra', C.c_int),
                        ('hInstance', T.HINSTANCE), ('hIcon', T.HICON),
                        ('hCursor', T.HANDLE), ('hbrBackground', T.HBRUSH),
                        ('lpszMenuName', T.LPCWSTR), ('lpszClassName', T.LPCWSTR)]
        class GUID(C.Structure):
            _fields_ = [('Data1',T.DWORD),('Data2',T.WORD),('Data3',T.WORD),('Data4',T.BYTE*8)]
        class NID(C.Structure):
            _fields_ = [('cbSize',T.DWORD),('hWnd',T.HWND),('uID',T.UINT),
                        ('uFlags',T.UINT),('uCallbackMessage',T.UINT),('hIcon',T.HICON),
                        ('szTip',T.WCHAR*128),('dwState',T.DWORD),('dwStateMask',T.DWORD),
                        ('szInfo',T.WCHAR*256),('uTimeout',T.UINT),('szInfoTitle',T.WCHAR*64),
                        ('dwInfoFlags',T.DWORD),('guidItem',GUID),('hBalloonIcon',T.HICON)]
        k.GetModuleHandleW.argtypes = [T.LPCWSTR]; k.GetModuleHandleW.restype = T.HMODULE
        u.DefWindowProcW.argtypes = [T.HWND,T.UINT,T.WPARAM,T.LPARAM]; u.DefWindowProcW.restype = LRESULT
        u.RegisterClassW.argtypes = [C.POINTER(WNDCLASS)]; u.RegisterClassW.restype = T.ATOM
        u.CreateWindowExW.argtypes = [T.DWORD,T.LPCWSTR,T.LPCWSTR,T.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,T.HWND,T.HMENU,T.HINSTANCE,T.LPVOID]
        u.CreateWindowExW.restype = T.HWND
        u.LoadImageW.argtypes = [T.HINSTANCE,T.LPCWSTR,T.UINT,C.c_int,C.c_int,T.UINT]; u.LoadImageW.restype = T.HANDLE
        u.RegisterWindowMessageW.argtypes = [T.LPCWSTR]; u.RegisterWindowMessageW.restype = T.UINT
        u.DestroyWindow.argtypes = [T.HWND]
        u.DestroyIcon.argtypes = [T.HICON]
        u.UnregisterClassW.argtypes = [T.LPCWSTR,T.HINSTANCE]
        u.GetMessageW.argtypes = [C.POINTER(T.MSG),T.HWND,T.UINT,T.UINT]; u.GetMessageW.restype = C.c_int
        u.TranslateMessage.argtypes = [C.POINTER(T.MSG)]
        u.DispatchMessageW.argtypes = [C.POINTER(T.MSG)]; u.DispatchMessageW.restype = LRESULT
        shell.Shell_NotifyIconW.argtypes = [T.DWORD,C.POINTER(NID)]; shell.Shell_NotifyIconW.restype = T.BOOL
        callback_message = 0x8001
        taskbar_created = u.RegisterWindowMessageW('TaskbarCreated')
        instance = k.GetModuleHandleW(None)
        icon = u.LoadImageW(None,self.icon_path,1,32,32,0x0010)
        if not icon:
            raise C.WinError(C.get_last_error())
        nid = NID()
        nid.cbSize = C.sizeof(nid)
        nid.uID = 1; nid.uFlags = 1|2|4
        nid.uCallbackMessage = callback_message; nid.hIcon = icon
        nid.szTip = '海绵桌面宠物 — 点击打开设置'
        @WNDPROC
        def proc(hwnd, msg, wp, lp):
            if msg == callback_message:
                # Legacy icon callback semantics: lParam contains the mouse message.
                if lp in (0x0202,0x0205,0x0203):
                    self.events.put(('settings',None))
                return 0
            if msg == taskbar_created:
                shell.Shell_NotifyIconW(0,C.byref(nid))
                return 0
            if msg == 0x0010:
                shell.Shell_NotifyIconW(2,C.byref(nid))
                u.DestroyWindow(hwnd)
                return 0
            if msg == 0x0002:
                u.PostQuitMessage(0)
                return 0
            return u.DefWindowProcW(hwnd,msg,wp,lp)
        name = f'SpongePetTray_{id(self)}'
        wc = WNDCLASS(); wc.lpfnWndProc=proc; wc.hInstance=instance; wc.lpszClassName=name
        if not u.RegisterClassW(C.byref(wc)):
            u.DestroyIcon(icon)
            raise C.WinError(C.get_last_error())
        try:
            self.hwnd = u.CreateWindowExW(0,name,name,0,0,0,0,0,None,None,instance,None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            nid.hWnd = self.hwnd
            if not shell.Shell_NotifyIconW(0,C.byref(nid)):
                u.DestroyWindow(self.hwnd)
                raise RuntimeError('Could not create notification-area icon')
            if self.stopping.is_set():
                u.PostMessageW(self.hwnd,0x0010,0,0)
            msg = T.MSG()
            while True:
                result = u.GetMessageW(C.byref(msg),None,0,0)
                if result <= 0:
                    break
                u.TranslateMessage(C.byref(msg));u.DispatchMessageW(C.byref(msg))
        finally:
            shell.Shell_NotifyIconW(2,C.byref(nid))
            self.hwnd = None
            u.UnregisterClassW(name,instance)
            u.DestroyIcon(icon)
