"""Главное окно VexPN (Windows) — визуал как в ios/VexPN/HomeView.swift + TUN (sing-box)."""
from __future__ import annotations

import logging
import re
import sys
import threading
import time
import uuid
import tkinter as tk
from tkinter import messagebox, Menu, TclError

import customtkinter as ctk

from . import __version__
from .api_client import ResolveKeyResponse, resolve_key, response_to_vpn_key
from .key_store import VpnKey, load_keys, save_keys
from .settings_store import AppSettings
from .gif_ctk import GifPlayer, ctk_image_from_asset
from .theme import ACCENT, ACCENT_HOVER, BG, CARD, SECONDARY_TEXT
from .vpn_process import SingBoxRunner

log = logging.getLogger(__name__)

VEX_RE = re.compile(r"VEX[A-Za-z0-9]{9}")

# CTkFont нельзя создавать на уровне модуля (нужен root) — шрифты в виде family/size
def _font(ui: int, w: str = "normal", mono: bool = False) -> tuple:
    fam = "Consolas" if mono else "Segoe UI"
    if w == "bold":
        return (fam, ui, "bold")
    return (fam, ui)


def extract_vex_key(text: str) -> str | None:
    m = VEX_RE.search(text)
    return m.group(0) if m else None


class VexPNApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk(fg_color=BG)
        self.root.title("VexPN")
        self.root.minsize(400, 560)
        self.root.geometry("450x700")

        self.settings = AppSettings.load()
        self.keys: list[VpnKey] = load_keys()
        self.active_id: uuid.UUID | None = self._restore_active_id()
        self.is_connected = False
        self.connection_t0: float | None = None
        self.elapsed_job: str | None = None
        self.runner = SingBoxRunner()
        self.resolving = False
        self.edit_mode = False
        self.selected_for_delete: set[uuid.UUID] = set()

        self._img_con_dis = None
        self._img_con_pau = None
        self._build_ui()
        self._tick()
        if not self.is_connected and hasattr(self, "f_timer"):
            self.f_timer.grid_remove()

    def _restore_active_id(self) -> uuid.UUID | None:
        if not self.keys:
            return None
        return self.keys[0].id

    def _build_ui(self) -> None:
        self.tab = ctk.CTkTabview(
            self.root,
            fg_color=BG,
            segmented_button_fg_color=CARD,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color="#E5E5EA",
            corner_radius=12,
        )
        self.tab.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        t_home = self.tab.add("  Главная  ")
        t_buy = self.tab.add("  Купить  ")
        t_set = self.tab.add("  Настройки  ")
        self._build_tab_home(t_home)
        self._build_tab_buy(t_buy)
        self._build_tab_settings(t_set)

    def _build_tab_home(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=0)
        parent.grid_rowconfigure(3, weight=1)

        # Таймер (как iOS)
        self.f_timer = ctk.CTkFrame(parent, fg_color=BG)
        self.f_timer.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            self.f_timer, text="Время подключения", text_color=SECONDARY_TEXT[0], font=_font(12)
        ).pack()
        self.lbl_time = ctk.CTkLabel(
            self.f_timer, text="00:00:00", text_color=ACCENT, font=_font(18, w="bold", mono=True)
        )
        self.lbl_time.pack(pady=4)
        self.f_timer.grid_remove()

        f_conn = ctk.CTkFrame(parent, fg_color=BG)
        f_conn.grid(row=1, column=0, pady=6)
        # iOS-parity: OFF=IMG_8971, ON=IMG_8970
        self._img_con_dis = ctk_image_from_asset("IMG_8971.PNG", (210, 210))
        self._img_con_pau = ctk_image_from_asset("IMG_8970.PNG", (210, 210))
        if not self._img_con_dis:
            self._img_con_dis = ctk_image_from_asset("connection_disconnected.png", (210, 210))
        if not self._img_con_pau:
            self._img_con_pau = ctk_image_from_asset("connection_connected.png", (210, 210))
        use_img = bool(self._img_con_dis and self._img_con_pau)
        self.btn_connect = ctk.CTkButton(
            f_conn,
            text="" if use_img else "▶",
            image=self._img_con_dis if use_img else None,
            width=220,
            height=220,
            corner_radius=110,
            font=_font(10) if use_img else _font(64, w="bold"),
            fg_color=BG,
            border_width=0,
            hover_color=ACCENT if not use_img else "#EDE7FF",
            text_color=ACCENT,
            command=self._on_toggle,
        )
        if use_img:
            self.btn_connect.configure(fg_color=BG, hover_color="#E8E0FF")
        self.btn_connect.pack()
        self.lbl_state = ctk.CTkLabel(
            f_conn,
            text="Не подключено",
            text_color=SECONDARY_TEXT[0],
            font=_font(16, w="bold"),
        )
        self.lbl_state.pack(pady=(10, 0))
        ctk.CTkLabel(
            f_conn,
            text="sing-box TUN · чаще нужны права администратора",
            text_color=SECONDARY_TEXT[0],
            font=_font(9),
        ).pack(pady=(2, 0))
        self._update_connect_state()

        bar = ctk.CTkFrame(parent, fg_color=BG)
        bar.grid(row=2, column=0, sticky="ew", pady=10)
        bar.grid_columnconfigure(0, weight=0)
        bar.grid_columnconfigure(1, weight=0)
        bar.grid_columnconfigure(2, weight=1)
        bar.grid_columnconfigure(3, weight=0)
        self.btn_mode = ctk.CTkButton(
            bar,
            text="Изменить",
            width=96,
            height=32,
            command=self._toggle_edit_mode,
            fg_color=CARD,
            text_color=ACCENT,
            border_width=1,
            border_color=ACCENT,
            hover_color="#E8E0FF",
        )
        self.btn_mode.grid(row=0, column=0, padx=(0, 4), sticky="w")
        self.btn_delete_batch = ctk.CTkButton(
            bar,
            text="Удалить",
            width=80,
            height=32,
            state="disabled",
            fg_color="#FF3B30",
            hover_color="#C62828",
            command=self._delete_batch,
        )
        self.btn_delete_batch.grid(row=0, column=1, padx=0, sticky="w")
        self.btn_delete_batch.grid_remove()
        ctk.CTkLabel(bar, text="").grid(row=0, column=2, sticky="ew")
        self.add_menu_btn = ctk.CTkButton(
            bar,
            text="＋",
            width=44,
            height=32,
            font=_font(20, w="bold"),
            command=self._show_add_menu,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        )
        self.add_menu_btn.grid(row=0, column=3, padx=(0, 0), sticky="e")

        sec = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12, border_width=0)
        sec.grid(row=3, column=0, sticky="nsew", pady=(0, 4), padx=0)
        prof_hdr = ctk.CTkFrame(sec, fg_color=CARD)
        prof_hdr.pack(anchor="w", fill=tk.X, padx=8, pady=(8, 2))
        h_g = ctk.CTkFrame(prof_hdr, fg_color="transparent")
        h_g.pack(side=tk.LEFT, padx=(4, 0))
        GifPlayer(h_g, "thunder.gif", (16, 16)).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkLabel(
            prof_hdr, text="Профили VexPN", font=_font(16, w="bold"), text_color=ACCENT, anchor="w"
        ).pack(side=tk.LEFT)
        self._keys_frame = ctk.CTkScrollableFrame(sec, fg_color=CARD, height=220)
        self._keys_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 8))
        self._refresh_key_rows()
        self._sync_edit_mode_ui()

    def _update_connect_state(self) -> None:
        ready = self._can_connect() and not self.resolving
        has_img = bool(self._img_con_dis and self._img_con_pau)
        self.btn_connect.configure(state="normal" if ready else "disabled")
        try:
            self.btn_connect.configure(bg_color=BG)
        except (tk.TclError, ValueError):
            pass
        if self.is_connected and has_img:
            self.btn_connect.configure(
                text="",
                image=self._img_con_pau,
                state="normal",
                fg_color=BG,
                hover_color="#E8E0FF",
            )
            self.btn_connect.configure(state="normal")
            return
        if self.is_connected and not has_img:
            self.btn_connect.configure(
                text="⏸",
                fg_color=ACCENT,
                state="normal",
                hover_color=ACCENT_HOVER,
                image=None,
            )
            return
        if has_img and ready and not self.resolving:
            self.btn_connect.configure(
                text="",
                image=self._img_con_dis,
                state="normal",
                fg_color=BG,
                hover_color="#E8E0FF",
            )
            self.btn_connect.configure(state="normal")
            return
        if has_img and not ready:
            self.btn_connect.configure(
                text="",
                image=self._img_con_dis,
                state="disabled",
                fg_color=BG,
                text_color=ACCENT,
            )
            return
        # без PNG — только «▶»
        self.btn_connect.configure(
            text="▶",
            image=None,
            fg_color=ACCENT if ready else "#C7C7CC",
            state="normal" if ready else "disabled",
            hover_color=ACCENT_HOVER,
        )

    def _can_connect(self) -> bool:
        k = self._active_key()
        return bool(k and k.vless_uri and k.vless_uri.strip())

    def _toggle_edit_mode(self) -> None:
        self.edit_mode = not self.edit_mode
        if not self.edit_mode:
            self.selected_for_delete.clear()
        self._sync_edit_mode_ui()
        self._refresh_key_rows()

    def _sync_edit_mode_ui(self) -> None:
        self.btn_mode.configure(text="Готово" if self.edit_mode else "Изменить")
        d_st = "normal" if (self.edit_mode and self.selected_for_delete) else "disabled"
        self.btn_delete_batch.configure(state=d_st)
        if self.edit_mode:
            self.btn_delete_batch.grid()
        else:
            self.btn_delete_batch.grid_remove()
        self.add_menu_btn.configure(state="normal" if not self.edit_mode else "disabled")

    def _show_add_menu(self) -> None:
        m = Menu(self.root, tearoff=0, font=("Segoe UI", 10))
        m.add_command(label="Добавить из буфера", command=self._add_clipboard)
        m.add_command(label="Ручной ввод ключа", command=self._add_manual)
        m.add_command(label="Сканер QR (позже)", state="disabled", command=None)
        try:
            m.tk_popup(
                self.add_menu_btn.winfo_rootx() - 40,
                self.add_menu_btn.winfo_rooty() + self.add_menu_btn.winfo_height(),
            )
        finally:
            m.grab_release()

    def _on_key_tap(self, k: VpnKey) -> None:
        if self.edit_mode:
            if k.id in self.selected_for_delete:
                self.selected_for_delete.discard(k.id)
            else:
                self.selected_for_delete.add(k.id)
            d_st = "normal" if self.selected_for_delete else "disabled"
            self.btn_delete_batch.configure(state=d_st)
        else:
            if self.is_connected and self.active_id is not None and k.id != self.active_id:
                self._disconnect()
            self.active_id = k.id
        self._refresh_key_rows()
        self._update_connect_state()

    def _refresh_key_rows(self) -> None:
        for w in self._keys_frame.winfo_children():
            w.destroy()
        for k in self.keys:
            active = (k.id == self.active_id) and (not self.edit_mode)
            marked = (k.id in self.selected_for_delete) and self.edit_mode
            row = ctk.CTkFrame(
                self._keys_frame,
                fg_color=("#F9F9FB", "#F9F9FB") if not (active or marked) else ("#EFE8FF", "#EFE8FF"),
                corner_radius=8,
            )
            row.pack(fill=tk.X, pady=3, padx=2)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill=tk.X, padx=8, pady=6)
            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill=tk.X)
            dot = "◉" if (active and not self.edit_mode) or marked else "○"
            ctk.CTkLabel(
                top, text=dot, text_color=ACCENT, width=18, font=_font(13)
            ).pack(side=tk.LEFT, padx=(0, 2))
            GifPlayer(top, "spider-crawl-folder.gif", (20, 20)).pack(side=tk.LEFT, padx=(0, 6))
            tcol = ctk.CTkFrame(top, fg_color="transparent")
            tcol.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ctk.CTkLabel(tcol, text=k.name, font=_font(15), anchor="w").pack(anchor="w")
            subl = ctk.CTkFrame(tcol, fg_color="transparent")
            subl.pack(anchor="w", fill=tk.X)
            GifPlayer(subl, "hour-glass.gif", (12, 12)).pack(side=tk.LEFT, padx=(0, 4), pady=(0, 2))
            ctk.CTkLabel(
                subl,
                text=f"Осталось: {k.remaining_days} дней",
                text_color=SECONDARY_TEXT[0],
                font=_font(12),
                anchor="w",
            ).pack(side=tk.LEFT, anchor="w")
            if not self.edit_mode:
                ctk.CTkButton(
                    top,
                    text="Удалить",
                    width=64,
                    height=28,
                    font=_font(12),
                    fg_color="transparent",
                    text_color="#FF3B30",
                    hover_color="#FFEBE9",
                    border_width=0,
                    command=lambda _k=k: self._delete_key_one(_k),
                ).pack(side=tk.RIGHT, padx=(2, 0))
            for w2 in (row, inner, top, tcol, subl):
                w2.bind("<Button-1>", lambda e, _k=k: self._on_key_tap(_k))
            for ch in (top, tcol, subl):
                for c in ch.winfo_children():
                    if (
                        isinstance(c, ctk.CTkButton)
                        and c.cget("text") == "Удалить"  # noqa: S105
                    ):
                        continue
                    c.bind("<Button-1>", lambda e, _k=k: self._on_key_tap(_k))

    def _delete_key_one(self, k: VpnKey) -> None:
        if not messagebox.askyesno("VexPN", f"Удалить ключ {k.access_key}?"):
            return
        if self.is_connected:
            self._disconnect()
        self.keys = [x for x in self.keys if x.id != k.id]
        if self.active_id == k.id:
            self.active_id = self.keys[0].id if self.keys else None
        save_keys(self.keys)
        self._update_connect_state()
        self._refresh_key_rows()

    def _delete_batch(self) -> None:
        if not self.selected_for_delete:
            return
        n = len(self.selected_for_delete)
        if not messagebox.askyesno("VexPN", f"Удалить выбранные профили: {n} шт.?"):
            return
        if self.is_connected:
            self._disconnect()
        new_ids = {i for i in self.selected_for_delete}
        self.keys = [k for k in self.keys if k.id not in new_ids]
        self.selected_for_delete.clear()
        self.edit_mode = False
        self._sync_edit_mode_ui()
        self.active_id = self.keys[0].id if self.keys else None
        save_keys(self.keys)
        self._update_connect_state()
        self._refresh_key_rows()

    def _on_toggle(self) -> None:
        if self.resolving:
            return
        if self.is_connected:
            self._disconnect()
            return
        if not self._can_connect():
            messagebox.showerror("VexPN", "Нет vless-ссылки. Проверьте активный VPN тариф.")
            return
        k = self._active_key()
        if not k or not k.vless_uri:
            return
        ok, msg = self.runner.start(k.vless_uri)
        if not ok:
            messagebox.showerror("VexPN", msg or "Не удалось запустить sing-box")
            return
        if msg:
            messagebox.showwarning("VexPN", msg)
        self.is_connected = True
        self.connection_t0 = time.time()
        if hasattr(self, "f_timer") and self.f_timer:
            self.f_timer.grid()
        self.lbl_state.configure(text="Подключено", text_color=ACCENT)
        self._update_connect_state()
        self._poll_singbox()

    def _poll_singbox(self) -> None:
        err = self.runner.check_alive()
        if err:
            messagebox.showerror("VexPN", err)
            self._disconnect_internal()
            return
        if self.is_connected and self.runner.running:
            self.root.after(2000, self._poll_singbox)

    def _disconnect(self) -> None:
        self.runner.stop()
        self._disconnect_internal()

    def _disconnect_internal(self) -> None:
        self.is_connected = False
        self.connection_t0 = None
        if hasattr(self, "f_timer") and self.f_timer is not None:
            self.f_timer.grid_remove()
        if hasattr(self, "lbl_time") and self.lbl_time is not None:
            self.lbl_time.configure(text="00:00:00")
        self.lbl_state.configure(text="Не подключено", text_color=SECONDARY_TEXT[0])
        self._update_connect_state()

    def _tick(self) -> None:
        if self.is_connected and self.connection_t0 is not None:
            s = int(time.time() - self.connection_t0)
            h, m, sec = s // 3600, (s % 3600) // 60, s % 60
            if hasattr(self, "lbl_time") and self.lbl_time is not None:
                self.lbl_time.configure(text=f"{h:02d}:{m:02d}:{sec:02d}")
        self.elapsed_job = self.root.after(1000, self._tick)

    def _add_clipboard(self) -> None:
        self.root.update()
        try:
            t = self.root.clipboard_get()
        except TclError:
            t = ""
        t = (t or "").strip()
        if not t:
            messagebox.showinfo("VexPN", "Буфер пустой.")
            return
        k = extract_vex_key(t) or t
        self._run_resolve(k, "clipboard")

    def _add_manual(self) -> None:
        t = ctk.CTkToplevel(self.root)
        t.title("Ручной ввод ключа")
        t.transient(self.root)
        t.resizable(False, False)
        t.configure(fg_color=BG)
        t.geometry("420x220")
        t.grab_set()
        ctk.CTkLabel(
            t,
            text="Введите ваш уникальный ключ VEX (12 символов, VEX…).",
            text_color=SECONDARY_TEXT[0],
            font=_font(13),
            wraplength=380,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=20, pady=(20, 8))
        ent = ctk.CTkEntry(
            t, width=360, height=40, font=_font(15, mono=True), placeholder_text="VEX…"
        )
        ent.pack(padx=20, pady=4)
        ent.focus_set()
        bf = ctk.CTkFrame(t, fg_color=BG)
        bf.pack(fill=tk.BOTH, expand=True, pady=16, padx=20)

        def on_cancel() -> None:
            t.grab_release()
            t.destroy()

        def on_add() -> None:
            s = (ent.get() or "").strip()
            t.grab_release()
            t.destroy()
            if s:
                self._run_resolve(extract_vex_key(s) or s, "manual")

        ent.bind("<Return>", lambda _e: on_add())
        ctk.CTkButton(
            bf,
            text="Добавить",
            width=120,
            height=36,
            font=_font(14, w="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=on_add,
        ).pack(side=tk.RIGHT, padx=(0, 4))
        ctk.CTkButton(
            bf,
            text="Отмена",
            width=100,
            height=36,
            font=_font(14),
            fg_color="#E5E5EA",
            hover_color="#D0D0D0",
            text_color="#1C1C1E",
            command=on_cancel,
        ).pack(side=tk.RIGHT)
        self.root.update_idletasks()
        t.update_idletasks()
        try:
            t.geometry("+%d+%d" % (self.root.winfo_x() + 24, self.root.winfo_y() + 64))
        except (tk.TclError, ValueError, RuntimeError):
            pass
        t.lift()

    def _run_resolve(self, raw: str, source: str) -> None:
        key = raw.strip()
        if not (key.startswith("VEX") and len(key) == 12 and key.isalnum()):
            messagebox.showerror("VexPN", "Неверный формат ключа (12 символов, VEX…).")
            return

        def work() -> None:
            r = resolve_key(self.settings.api_base_url, key)
            self.root.after(0, lambda: self._resolve_done(r, source))

        self.resolving = True
        self._update_connect_state()
        threading.Thread(target=work, name="resolve", daemon=True).start()

    def _resolve_done(self, r: ResolveKeyResponse, source: str) -> None:
        self.resolving = False
        self._update_connect_state()
        if not r.ok and r.error_message:
            messagebox.showerror("VexPN", r.error_message)
            return
        if r.ok and not r.active and r.error_message:
            messagebox.showerror("VexPN", r.error_message)
            return
        if r.ok and not r.active:
            messagebox.showerror("VexPN", "Нет активного VPN тарифа.")
            return
        if not (r.ok and r.active and r.vless_uri):
            messagebox.showerror("VexPN", "Сервер не вернул vless-ссылку.")
            return
        nk = response_to_vpn_key(r)
        for i, ex in enumerate(self.keys):
            if ex.access_key == nk.access_key:
                nk = VpnKey(
                    id=ex.id,
                    access_key=nk.access_key,
                    name=nk.name,
                    remaining_days=nk.remaining_days,
                    vless_uri=nk.vless_uri,
                )
                self.keys[i] = nk
                self.active_id = nk.id
                break
        else:
            self.keys.append(nk)
            self.active_id = nk.id
        save_keys(self.keys)
        self._refresh_key_rows()
        self._update_connect_state()
        if source == "clipboard":
            messagebox.showinfo("VexPN", "Ключ добавлен из буфера.")
        else:
            messagebox.showinfo("VexPN", "Ключ успешно добавлен.")

    def _build_tab_buy(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            parent,
            text="Купить",
            font=_font(32, w="bold"),
            text_color="#1C1C1E",
        ).grid(row=0, column=0, pady=(24, 0), padx=20, sticky=tk.S)
        ctk.CTkLabel(
            parent,
            text="Оформление и оплата VexPN, как в приложении для iOS — скоро здесь.",
            text_color=SECONDARY_TEXT[0],
            font=_font(15),
            justify=tk.CENTER,
        ).grid(row=1, column=0, pady=16, padx=28, sticky=tk.N)
        ctk.CTkButton(
            parent,
            text="Открыть в Telegram",
            width=220,
            height=44,
            font=_font(16, w="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=12,
            command=lambda: messagebox.showinfo(
                "VexPN", "Откройте бота Vex в Telegram (как в iOS) вручную в Telegram Desktop."
            ),
        ).grid(row=2, column=0, pady=(0, 48), sticky=tk.N)

    def _build_tab_settings(self, parent) -> None:
        ctk.CTkLabel(
            parent,
            text="Настройки",
            font=_font(32, w="bold"),
            text_color="#1C1C1E",
        ).pack(anchor=tk.W, padx=4, pady=(12, 4))
        s = ctk.CTkScrollableFrame(parent, fg_color=BG, height=450)
        s.pack(fill=tk.BOTH, expand=True, padx=0, pady=4)

        def group_row(t: str, fn) -> None:
            c = ctk.CTkFrame(s, fg_color=CARD, corner_radius=10, border_width=0)
            c.pack(fill=tk.X, pady=5, padx=2)
            ctk.CTkButton(
                c,
                text=t,
                anchor=tk.W,
                font=_font(16),
                height=50,
                fg_color=CARD,
                text_color="#1C1C1E",
                hover_color="#EFE8FF",
                border_width=0,
                command=fn,
            ).pack(fill=tk.X, padx=0, pady=0)

        group_row("Base URL (VEXPN_API_BASE_URL, как в iOS)", self._open_url_dialog)
        group_row("Конфиденциальность", lambda: messagebox.showinfo("VexPN", "Скоро, как в iOS."))
        group_row("Сбор данных", lambda: messagebox.showinfo("VexPN", "Скоро, как в iOS."))
        group_row("Условия использования", lambda: messagebox.showinfo("VexPN", "См. vex-gram.ru"))
        ctk.CTkLabel(
            s,
            text=f"Версия {__version__} · {self.settings.api_base_url}",
            text_color=SECONDARY_TEXT[0],
            font=_font(11),
        ).pack(anchor=tk.W, padx=8, pady=16)

    def _open_url_dialog(self) -> None:
        d = ctk.CTkInputDialog(
            text="Base URL (без / в конце, как VEXPN_API_BASE_URL):",
            title="Backend API",
        )
        ent = getattr(d, "_entry", None)
        if ent is not None:
            ent.delete(0, tk.END)
            ent.insert(0, self.settings.api_base_url)
        u = d.get_input()
        if u is None or u is False or u is True:
            return
        u = (u or "").strip().rstrip("/")
        if not u.startswith("http"):
            messagebox.showerror("VexPN", "Некорректный URL (нужен http(s)://)")
            return
        self.settings.api_base_url = u
        self.settings.save()
        messagebox.showinfo("VexPN", f"Сохранено: {u}")

    def _active_key(self) -> VpnKey | None:
        if not self.active_id:
            return None
        for k in self.keys:
            if k.id == self.active_id:
                return k
        return None

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if sys.platform == "win32":
        try:
            from ctypes import windll  # type: ignore

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        # Для TUN на Windows нужны admin rights: если не админ — перезапускаем через UAC.
        try:
            import ctypes  # type: ignore

            if not bool(ctypes.windll.shell32.IsUserAnAdmin()):  # type: ignore[attr-defined]
                exe = sys.executable
                params = " ".join(f'"{a}"' for a in sys.argv[1:])
                rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)  # type: ignore[attr-defined]
                if int(rc) <= 32:
                    messagebox.showerror(
                        "VexPN",
                        "Для подключения VPN нужны права администратора.\nЗапустите VexPN от имени администратора.",
                    )
                return
        except Exception:
            pass
    VexPNApp().run()


if __name__ == "__main__":
    main()
