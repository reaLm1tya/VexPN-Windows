"""Проигрыватель анимированных GIF для CustomTkinter (как AnimatedGIFIcon в iOS)."""
from __future__ import annotations

import customtkinter as ctk
from PIL import Image, ImageTk

from .paths import asset_path

__all__ = ["GifPlayer", "ctk_image_from_asset"]


def ctk_image_from_asset(name: str, size: tuple[int, int]):
    p = asset_path(name)
    if p is None:
        return None
    try:
        from customtkinter import CTkImage

        im = Image.open(p)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        if im.size != size:
            im = im.resize(size, Image.Resampling.LANCZOS)
        return CTkImage(light_image=im, size=size)
    except OSError:
        return None


class GifPlayer(ctk.CTkFrame):
    """Проигрывает .gif; при отсутствии файла пусто (см. fallback в app)."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        name: str,
        size: tuple[int, int],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color=kwargs.pop("fg_color", "transparent"), **kwargs)
        self._w, self._h = size[0], size[1]
        self._name = name
        self._frames: list[ImageTk.PhotoImage] = []
        self._durs: list[int] = []
        self._i = 0
        self._job: str | None = None
        self._has_gif = False
        p = asset_path(name)
        if p is not None and p.suffix.lower() in (".gif", ".GIF"):
            try:
                with Image.open(p) as im:
                    n = getattr(im, "n_frames", 1)
                    for f in range(n):
                        im.seek(f)
                        frame = im.convert("RGBA")
                        d = im.info.get("duration", 100) or 100
                        self._durs.append(max(int(d), 20))
                        frame = frame.resize((self._w, self._h), Image.Resampling.LANCZOS)
                        self._frames.append(ImageTk.PhotoImage(frame))
            except (OSError, ValueError, EOFError):
                self._frames = []
        self._label = ctk.CTkLabel(
            self,
            text="",
            width=size[0],
            height=size[1],
        )
        self._label.pack()
        self._has_gif = bool(self._frames)
        if self._has_gif:
            self._tick()

    def set_visible(self, ok: bool) -> None:
        if ok and self._has_gif and self._job is None:
            self._tick()
        if not ok and self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def _tick(self) -> None:
        if not self._frames:
            return
        f = self._frames[self._i]
        self._label.configure(image=f)
        d = self._durs[self._i]
        self._i = (self._i + 1) % len(self._frames)
        self._job = self.after(d, self._tick)

    def destroy(self) -> None:  # noqa: A003
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()
