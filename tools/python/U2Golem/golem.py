"""Drive Golem Studio (Unreal II's GlmEd.exe) from Python.

Golem Studio has no command line, so this clicks its workspace tree and answers its
dialogs. What makes that work (learned the hard way, 2026-09-30):
  * System\\dxgi.dll ("BGProxy", not part of the game) makes the tool's windows fight
    over focus and no popup menu ever opens: it is renamed for the session.
  * The Render and Entity windows take the foreground whenever they redraw: they are
    closed before the tree is used.
  * Popup menus need a real right-click on a tree item that already has focus; menu
    entries are then picked with the keyboard (Windows dialogs here are in Portuguese:
    Sim / Nao / Abrir).
The real mouse is used, so nobody should touch the PC during a run.
"""
import contextlib
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time
import warnings

warnings.filterwarnings("ignore", message="32-bit application")
from pywinauto import Application, mouse
from pywinauto.keyboard import send_keys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
SYSTEM = os.path.join(GAME, "System")
MESHES = os.path.join(GAME, "Meshes")
u = ctypes.windll.user32


@contextlib.contextmanager
def no_bgproxy():
    dll, off = os.path.join(SYSTEM, "dxgi.dll"), os.path.join(SYSTEM, "dxgi.dll.off-golem")
    moved = False
    if os.path.exists(dll) and not os.path.exists(off):
        os.rename(dll, off); moved = True
    try:
        yield
    finally:
        if moved and os.path.exists(off) and not os.path.exists(dll):
            os.rename(off, dll)


def kill():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Name GlmEd -Force -ErrorAction SilentlyContinue"], capture_output=True)
    time.sleep(1.5)


def popup_menus():
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(h, buf, 64)
        if buf.value == "#32768" and u.IsWindowVisible(h):
            found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found


def menu_items():
    out = []
    for m in popup_menus():
        hm = u.SendMessageW(m, 0x01E1, 0, 0)          # MN_GETHMENU
        for i in range(u.GetMenuItemCount(hm)):
            b = ctypes.create_unicode_buffer(128)
            u.GetMenuStringW(hm, i, b, 128, 0x400)
            out.append(b.value)
    return out


def menu_pick(label):
    """Click the visible popup-menu entry whose text starts with label (hover opens submenus)."""
    for m in popup_menus():
        hm = u.SendMessageW(m, 0x01E1, 0, 0)
        for i in range(u.GetMenuItemCount(hm)):
            b = ctypes.create_unicode_buffer(128)
            u.GetMenuStringW(hm, i, b, 128, 0x400)
            if b.value.replace("&", "").startswith(label):
                r = wt.RECT()
                u.GetMenuItemRect(0, hm, i, ctypes.byref(r))
                x, y = (r.left + r.right) // 2, (r.top + r.bottom) // 2
                mouse.move(coords=(x, y)); time.sleep(0.5)
                mouse.click(coords=(x, y)); time.sleep(0.8)
                return True
    raise RuntimeError("no menu entry " + label + " in " + str(menu_items()))


class Golem:
    def __init__(self, workspace, log=print):
        self.log = log
        kill()
        self.app = Application(backend="win32").start(os.path.join(SYSTEM, "GlmEd.exe"), work_dir=SYSTEM)
        time.sleep(4)
        self.main = self.app.window(class_name="GLM_WIN_WEdMainWindow")
        self.main.menu_select("&File->&Open Workspace")
        time.sleep(1.5)
        dlg = self.app.window(title="Open Workspace", class_name="#32770")
        dlg.child_window(class_name="Edit").set_edit_text(workspace)
        time.sleep(0.3)
        dlg.child_window(class_name="Edit").type_keys("{ENTER}")
        for _ in range(120):                          # a big workspace takes a while to load
            time.sleep(1)
            if self.app.window(title="Workspace", class_name="#32770").exists():
                break
        time.sleep(2)
        self.close_viewers()
        self.ws = self.app.window(title="Workspace", class_name="#32770")
        self.tree = self.ws.child_window(class_name="SysTreeView32")
        self.to_side_monitor()

    def to_side_monitor(self):
        """Put Golem Studio on the leftmost monitor (other sessions test games on the primary one).
        Its dialogs open over the main window, so they follow it."""
        ox = u.GetSystemMetrics(76)                  # SM_XVIRTUALSCREEN: 0 with one monitor
        u.ShowWindow(self.main.handle, 9); time.sleep(0.3)        # SW_RESTORE
        u.MoveWindow(self.main.handle, ox, 0, 1900, 1000, True); time.sleep(0.3)
        u.ShowWindow(self.main.handle, 3); time.sleep(0.5)        # SW_MAXIMIZE (on that monitor)
        u.MoveWindow(self.ws.handle, ox + 1100, 100, 320, 850, True)
        time.sleep(0.5)

    def close_viewers(self):
        for w in self.app.windows():
            if w.is_visible() and (w.class_name() == "GLM_WIN_WEdRenderWindow" or w.window_text() == "Entity"):
                u.PostMessageW(w.handle, 0x0112, 0xF060, 0)   # WM_SYSCOMMAND SC_CLOSE
                time.sleep(0.8)

    def quit(self):
        kill()

    # ---- tree ----
    def item(self, path):
        return self.tree.get_item(path.split("/") if isinstance(path, str) else path)

    def children(self, path):
        try:
            return [c.text().rstrip(" *") for c in self.item(path).children()]
        except Exception:
            return []

    def menu(self, path, keys):
        """Right-click a tree item and click through its popup menu by entry labels."""
        it = self.item(path)
        it.ensure_visible()
        for attempt in range(5):
            cr, tr = it.client_rect(), self.tree.rectangle()
            x, y = tr.left + cr.left + 20, tr.top + (cr.top + cr.bottom) // 2
            self.wait_clear(x, y)
            mouse.click(coords=(x, y)); time.sleep(1.2)
            mouse.click(button="right", coords=(x, y)); time.sleep(1.0)
            if popup_menus():
                break
            self.close_viewers(); time.sleep(1.0)
        else:
            raise RuntimeError("no popup menu for " + str(path))
        for k in keys:                      # entries by label, e.g. ["New...", "Folder"]
            menu_pick(k)
        time.sleep(0.8)

    def wait_clear(self, x, y, timeout=600):
        """Wait until the screen point (x, y) shows our tree, not some other window on top
        (e.g. a game another session launched), so the real mouse can't click into it."""
        end, told = time.time() + timeout, False
        while time.time() < end:
            u.SetWindowPos(self.ws.handle, 0, 0, 0, 0, 0, 0x1 | 0x2 | 0x40)   # HWND_TOP, show
            h = u.WindowFromPoint(wt.POINT(x, y))
            if h == self.tree.handle:
                return
            if not told:
                buf = ctypes.create_unicode_buffer(128)
                u.GetWindowTextW(u.GetAncestor(h, 2), buf, 128)
                self.log("  waiting: another window covers Golem Studio (%s)" % buf.value)
                told = True
            time.sleep(3)
        raise RuntimeError("Golem Studio stayed covered")

    # ---- dialogs ----
    def dialogs(self):
        return [w for w in self.app.windows() if w.is_visible() and w.class_name() == "#32770"
                and w.window_text() not in ("Workspace", "Entity")]

    def wait_dialog(self, title=None, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            for d in self.dialogs():
                if title is None or title in d.window_text():
                    return d
            time.sleep(0.3)
        raise RuntimeError("no dialog " + str(title))

    @staticmethod
    def kids(d, cls, text=None):
        return [c for c in d.children() if c.class_name() == cls and (text is None or c.window_text().replace("&", "") == text)]

    def press(self, d, *names):
        for n in names:
            b = self.kids(d, "Button", n)
            if b:
                b[0].click(); time.sleep(0.8); return
        raise RuntimeError(f"no button {names} in {d.window_text()}")

    def answer_text(self, title, text):
        d = self.wait_dialog(title)
        self.kids(d, "Edit")[0].set_edit_text(text); time.sleep(0.2)
        self.press(d, "OK", "Abrir", "Open")

    def confirm(self, title):
        d = self.wait_dialog(title)
        text = " ".join(c.window_text() for c in self.kids(d, "Static"))
        self.press(d, "Sim", "Yes", "OK")
        return text

    def menu_dialog(self, path, keys, title, tries=3):
        """Menu clicks are occasionally lost (a redraw steals the click): retry until the dialog shows."""
        for attempt in range(tries):
            self.menu(path, keys)
            try:
                return self.wait_dialog(title, timeout=6)
            except RuntimeError:
                send_keys("{ESC}{ESC}")
                self.close_viewers()
                self.log("  (menu click lost, retrying %s)" % title)
                time.sleep(1.5)
        raise RuntimeError("no dialog " + title)

    # ---- operations ----
    def new_folder(self, parent, name):
        if name in self.children(parent):
            return
        self.menu_dialog(parent, ["New...", "Folder"], "New Folder")
        self.answer_text("New Folder", name)

    def new_file(self, folder, name):
        if name + ".gem" in self.children(folder):
            return
        self.menu_dialog(folder, ["New...", "File"], "New File")
        self.answer_text("New File", name)

    def import_psk_psa(self, gem, path, prefix, hierarchy=None, scripts=None):
        self.menu_dialog(gem, ["Import...", "Import .PSK"], "Import PSK/PSA")
        self.answer_text("Import PSK/PSA", path)
        self.answer_text("Object Prefix", prefix)
        if path.lower().endswith(".psa"):
            for title, want in (("Choose Hierarchy", hierarchy), ("Choose Scripts", scripts)):
                d = self.wait_dialog(title)
                shown = self.kids(d, "Edit")[0].window_text()
                if want and want not in shown:
                    raise RuntimeError(f"{title} offers {shown}, wanted {want}")
                self.press(d, "OK")
        return self.confirm("Confirm Import")

    def save(self, gem):
        self.menu(gem, ["Save"])
        try:
            self.confirm("Save File")                 # "Are you sure you want to save ...?"
        except RuntimeError:
            pass
        time.sleep(1.5)

    def edit_object(self, path):
        return self.menu_dialog(path, ["View/Modify"], "Edit Object")

    def set_stage_textures(self, materials_path, names_by_material):
        """Materials tab: each material's stage 0 texture = the given name."""
        d = self.edit_object(materials_path)

        def near(cls, x, y, text=None):
            r0 = d.rectangle()
            cs = self.kids(d, cls, text)
            cs.sort(key=lambda c: abs(c.rectangle().left - r0.left - x) + abs(c.rectangle().top - r0.top - y))
            return cs[0]
        combo = near("ComboBox", 46, 88)
        done = {}
        for i, mat in enumerate(combo.item_texts()):
            combo.select(i); time.sleep(0.6)
            want = names_by_material.get(mat, mat)
            for attempt in range(4):                  # the button sometimes ignores a click right after the combo changes
                near("Button", 557, 89, "Change").click()
                try:
                    self.wait_dialog("Texture Name", timeout=4)
                    break
                except RuntimeError:
                    time.sleep(1.0)
            self.answer_text("Texture Name", want)
            done[mat] = near("Edit", 392, 89).window_text()
        u.PostMessageW(d.handle, 0x0010, 0, 0)                     # WM_CLOSE
        time.sleep(0.8)
        return done

    # ---- blueprint attributes (a list view: rows are 16 px apart, the first at y=104) ----
    def to_side(self, w, x=200, y=200):
        r = w.rectangle()
        u.MoveWindow(w.handle, u.GetSystemMetrics(76) + x, y, r.width(), r.height(), True)
        time.sleep(0.5)
        return w.rectangle()

    def pick_object(self, title, path):
        """In an object picker (a tree of the workspace), select the object at path (below the root)."""
        from pywinauto.controls.common_controls import TreeViewWrapper
        d = self.wait_dialog(title)
        tv = TreeViewWrapper(self.kids(d, "SysTreeView32")[0].handle)
        full = [tv.roots()[0].text()] + list(path)
        for i in range(2, len(full)):
            tv.get_item(full[:i]).expand(); time.sleep(0.3)
        tv.get_item(full).select(); time.sleep(0.5)
        chosen = self.kids(d, "Edit")[0].window_text()
        self.press(d, "OK")
        return chosen

    def set_blueprint(self, path, scripts_path=None, floats=()):
        """scripts_path: where the Scripts object lives, e.g. ["Characters", "Biped", "ArmorAnims.gem",
        "Entity Scripts", "ArmorAnimsScripts"]; floats: [("OriginScale", 0.7027), ...] added as new rows.
        A fresh import's blueprint has two rows: Model, Scripts."""
        d = self.edit_object(path)
        r = self.to_side(d)
        value_x = r.left + 420
        row_y = lambda i: r.top + 104 + 16 * i
        def open_value(row, title):
            for attempt in range(4):                  # double-clicks are sometimes lost too
                mouse.double_click(coords=(value_x, row_y(row)))
                try:
                    return self.wait_dialog(title, timeout=4)
                except RuntimeError:
                    time.sleep(1.0)
            raise RuntimeError("no dialog " + title)

        if scripts_path:
            open_value(1, "Attribute Object Value")
            self.log("  scripts: " + self.pick_object("Attribute Object Value", scripts_path))
        for n, (attr, value) in enumerate(floats):
            mouse.click(button="right", coords=(r.left + 150, r.top + 300)); time.sleep(1.0)
            menu_pick("Create New Attribute"); time.sleep(0.6)
            menu_pick(attr); time.sleep(1.0)
            open_value(2 + n, "Attribute Float Value")
            self.answer_text("Attribute Float Value", "%g" % value)
            self.log("  %s = %g" % (attr, value))
        u.PostMessageW(d.handle, 0x0010, 0, 0)                     # WM_CLOSE
        time.sleep(0.8)

