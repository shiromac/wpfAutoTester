"""Screenshot capture utilities.

Uses PrintWindow with PW_RENDERFULLCONTENT to correctly capture
WPF hardware-accelerated (DirectX) windows that appear black with BitBlt.
Falls back to PIL.ImageGrab when no target window is available.
"""

from __future__ import annotations

import ctypes
import pathlib
from typing import Any, Optional

from PIL import Image, ImageGrab

from wpf_agent.core.target import ResolvedTarget

# Win32 constants
PW_RENDERFULLCONTENT = 0x00000002


def _capture_with_print_window(hwnd: int) -> Image.Image | None:
    """Capture a window using PrintWindow + PW_RENDERFULLCONTENT.

    This correctly renders WPF/DirectX hardware-accelerated content
    that appears black when captured with BitBlt (ImageGrab).
    """
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Get window dimensions including non-client area
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                     ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.top - rect.bottom  # intentional: will be negative
    if width <= 0:
        return None
    # Correct height
    height = rect.bottom - rect.top
    if height <= 0:
        return None

    # Create device context and bitmap
    hwnd_dc = user32.GetWindowDC(hwnd)
    if not hwnd_dc:
        return None

    try:
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        if not mem_dc:
            return None
        try:
            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            if not bitmap:
                return None
            try:
                gdi32.SelectObject(mem_dc, bitmap)

                # PrintWindow with PW_RENDERFULLCONTENT (Windows 8.1+)
                result = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
                if not result:
                    return None

                # Read bitmap bits into PIL Image
                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_long),
                        ("biHeight", ctypes.c_long), ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_long),
                        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", ctypes.c_uint32),
                        ("biClrImportant", ctypes.c_uint32),
                    ]

                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = width
                bmi.biHeight = -height  # top-down
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                bmi.biCompression = 0  # BI_RGB

                buf_size = width * height * 4
                buf = ctypes.create_string_buffer(buf_size)
                gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

                img = Image.frombuffer("RGBX", (width, height), buf, "raw", "BGRX", 0, 1)
                return img.convert("RGB")
            finally:
                gdi32.DeleteObject(bitmap)
        finally:
            gdi32.DeleteDC(mem_dc)
    finally:
        user32.ReleaseDC(hwnd, hwnd_dc)


def _enum_process_windows(pid: int) -> list[int]:
    """Return visible window handles belonging to *pid* using Win32 EnumWindows.

    pywinauto Desktop.windows() misses WPF popup HWNDs (ComboBox dropdowns,
    context menus, tooltips) because they lack UIA top-level window properties.
    Win32 EnumWindows catches them all.
    """
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

    hwnds: list[int] = []

    def _cb(hwnd: int, _lparam: Any) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        win_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
        if win_pid.value == pid:
            # Skip zero-area windows (hidden helper windows)
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                             ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            if (r.right - r.left) > 0 and (r.bottom - r.top) > 0:
                hwnds.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return hwnds


def _composite_process_windows(
    hwnds: list[int], main_hwnd: int
) -> Image.Image | None:
    """Composite all visible windows of a process into a single image.

    Captures each window via PrintWindow and pastes them onto a canvas
    based on screen coordinates. The main window is drawn first, then
    popups on top (matching visual Z-order).
    """
    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                     ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    # Collect rects for each handle
    win_info: list[tuple[int, tuple[int, int, int, int]]] = []
    for h in hwnds:
        rect = RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        r = (rect.left, rect.top, rect.right, rect.bottom)
        if r[2] - r[0] <= 0 or r[3] - r[1] <= 0:
            continue
        win_info.append((h, r))

    if not win_info:
        return None

    # Compute union bounding rect
    union_l = min(r[0] for _, r in win_info)
    union_t = min(r[1] for _, r in win_info)
    union_r = max(r[2] for _, r in win_info)
    union_b = max(r[3] for _, r in win_info)
    canvas_w = union_r - union_l
    canvas_h = union_b - union_t
    if canvas_w <= 0 or canvas_h <= 0:
        return None

    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))

    # Separate main window and popups; draw main first, popups on top
    main_items = [(h, r) for h, r in win_info if h == main_hwnd]
    popup_items = [(h, r) for h, r in win_info if h != main_hwnd]

    for hwnd, r in main_items + popup_items:
        cap = _capture_with_print_window(hwnd)
        if cap is None:
            continue
        x = r[0] - union_l
        y = r[1] - union_t
        canvas.paste(cap, (x, y))

    return canvas


def capture_screenshot(
    target: ResolvedTarget | None = None,
    region: dict[str, int] | None = None,
    save_path: pathlib.Path | None = None,
) -> pathlib.Path:
    """Capture a screenshot, optionally scoped to a window or region.

    For target windows, uses PrintWindow+PW_RENDERFULLCONTENT to handle
    WPF hardware-accelerated rendering. When popup windows (context menus,
    combo dropdowns, tooltips) belonging to the same process are detected,
    all windows are composited into a single image.
    Falls back to ImageGrab if needed.
    """
    img = None

    if target and not region:
        # Try PrintWindow first (handles WPF DirectX rendering)
        try:
            from wpf_agent.uia.engine import _top_window

            win = _top_window(target)
            main_hwnd = win.handle

            # Find all visible windows for this PID via Win32 EnumWindows
            # (pywinauto Desktop.windows() misses WPF popup HWNDs)
            popup_hwnds = _enum_process_windows(target.pid)

            if len(popup_hwnds) <= 1:
                # No popups — capture main window only (original path)
                if main_hwnd:
                    img = _capture_with_print_window(main_hwnd)
            else:
                # Popups detected — composite all windows
                img = _composite_process_windows(popup_hwnds, main_hwnd)
        except Exception:
            pass

    if img is None:
        # Fallback to ImageGrab (BitBlt-based)
        bbox = None
        if region:
            bbox = (region["left"], region["top"], region["right"], region["bottom"])
        elif target:
            try:
                from wpf_agent.uia.engine import _top_window
                win = _top_window(target)
                r = win.rectangle()
                bbox = (r.left, r.top, r.right, r.bottom)
            except Exception:
                pass
        img = ImageGrab.grab(bbox=bbox)

    if save_path is None:
        import tempfile
        fd = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        save_path = pathlib.Path(fd.name)
        fd.close()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(save_path), "PNG")
    return save_path
