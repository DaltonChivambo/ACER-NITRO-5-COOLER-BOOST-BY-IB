#!/usr/bin/env python3
"""Nitro 5 Cooler Boost - App desktop (apenas ventoinhas em RPM)."""

import fcntl
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from .core import NitroBoost
    from .insights import get_all_insights
except ImportError:
    from core import NitroBoost
    from insights import get_all_insights

BG = "#0d0d12"
CARD = "#16161d"
ACCENT = "#00d4aa"
ACCENT_DIM = "#00a884"
DANGER = "#ff4757"
TEXT = "#e8e8ed"
TEXT_MUTED = "#8b8b9a"
BORDER = "#2a2a35"
TRACK = "#2a2a35"
THUMB = "#00d4aa"


def _card(parent, **kw):
    f = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, **kw)
    return f


class Slider(tk.Frame):
    def __init__(self, parent, from_=0, to=100, value=50, width=200, height=28, **kw):
        super().__init__(parent, **kw)
        self.from_ = from_
        self.to = to
        self._value = max(from_, min(to, value))
        self._width = width
        self.height = height
        self._dragging = False
        self.configure(bg=parent.cget("bg") if hasattr(parent, "cget") else CARD)

        self.canvas = tk.Canvas(self, width=width, height=height, bg=CARD, highlightthickness=0, cursor="hand2")
        self.canvas.pack(side=tk.LEFT)
        self.label = tk.Label(self, text=f"{self._value}%", font=("", 10, "bold"), bg=CARD, fg=ACCENT, width=5)
        self.label.pack(side=tk.LEFT, padx=(10, 0))

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel_linux)
        self.canvas.bind("<Button-5>", self._on_wheel_linux)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel_linux)
        self.bind("<Button-5>", self._on_wheel_linux)
        self._draw()

    def get(self):
        return self._value

    def set(self, value):
        self._value = max(self.from_, min(self.to, int(value)))
        self.label.config(text=f"{self._value}%")
        self._draw()

    def _get_width(self):
        return self._width

    def _x_to_value(self, x):
        w = self._get_width() - 20
        if w <= 0:
            return self.from_
        frac = max(0, min(1, (x - 10) / w))
        return int(self.from_ + frac * (self.to - self.from_))

    def _value_to_x(self, v):
        w = self._get_width() - 20
        frac = (v - self.from_) / (self.to - self.from_) if self.to != self.from_ else 0
        return 10 + frac * w

    def _draw(self):
        self.canvas.delete("all")
        w = self._get_width()
        h = self.height // 2
        self.canvas.create_rectangle(8, h - 4, w - 12, h + 4, fill=TRACK, outline="")
        x = self._value_to_x(self._value)
        self.canvas.create_rectangle(8, h - 4, x, h + 4, fill=ACCENT_DIM, outline="")
        self.canvas.create_oval(x - 10, h - 10, x + 10, h + 10, fill=THUMB, outline=ACCENT_DIM, width=2)

    def _on_click(self, e):
        self._dragging = True
        self._set_from_x(e.x)

    def _on_drag(self, e):
        if self._dragging:
            self._set_from_x(e.x)

    def _on_release(self, e):
        self._dragging = False

    def _set_from_x(self, x):
        v = self._x_to_value(x)
        if v != self._value:
            self._value = v
            self.label.config(text=f"{self._value}%")
            self._draw()

    def _on_wheel(self, e):
        delta = 5 if e.delta > 0 else -5
        self.set(self._value + delta)

    def _on_wheel_linux(self, e):
        delta = 5 if e.num == 4 else -5
        self.set(self._value + delta)


class NitroBoostApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Acer Nitro 5 Cooler Boost by IB")
        self.root.configure(bg=BG)
        self.root.minsize(360, 420)
        self.root.geometry("400x520")
        self.root.resizable(True, True)

        self.boost = NitroBoost()
        self._cpu_boost = False
        self._gpu_boost = False
        self._poll_id = None
        self._lock_fd = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=8, font=("", 10))

        self._setup_ui()
        self._check_availability()
        self._start_poll()

    def _setup_ui(self):
        main = tk.Frame(self.root, bg=BG, padx=16, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(main, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="❄", font=("", 28), bg=BG, fg=ACCENT).pack(side=tk.LEFT, padx=(0, 12))
        tit = tk.Frame(header, bg=BG)
        tit.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(tit, text="Acer Nitro 5 Cooler Boost by IB", font=("", 18, "bold"), bg=BG, fg=TEXT).pack(anchor=tk.W)
        tk.Label(tit, text="AN515-44, 46, 56, 57, 58 • by IB", font=("", 9), bg=BG, fg=TEXT_MUTED).pack(anchor=tk.W)
        self.badge = tk.Label(header, text="...", font=("", 9), bg=BG, fg=TEXT_MUTED, padx=8, pady=4)
        self.badge.pack(side=tk.RIGHT)
        opts_btn = tk.Button(
            header, text=" ⚙ Opções ", font=("", 9), bg=BORDER, fg=TEXT,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self._toggle_opts,
            highlightthickness=0, borderwidth=0,
        )
        opts_btn.pack(side=tk.RIGHT, padx=(0, 8))

        # Painel Opções (oculto até clicar em Opções)
        self._opts_visible = False
        self.opts_panel = _card(main, padx=16, pady=12)
        tk.Label(self.opts_panel, text="OPÇÕES", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 10))
        uninstall_btn = tk.Button(
            self.opts_panel, text="  Desinstalar aplicativo  ", font=("", 10),
            bg=BORDER, fg=TEXT, activebackground=DANGER, activeforeground=TEXT,
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2", command=self._uninstall,
            highlightthickness=0, borderwidth=0,
        )
        uninstall_btn.pack(anchor=tk.W)
        self.opts_panel.pack_forget()

        # Conteúdo principal (opts_panel será inserido antes quando visível)
        self.content_frame = tk.Frame(main, bg=BG)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        content = self.content_frame

        # Ventoinhas (RPM + temperatura)
        fan_frame = _card(content, padx=16, pady=12)
        fan_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(fan_frame, text="CPU e GPU", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 12))
        cpu_info_row = tk.Frame(fan_frame, bg=CARD)
        cpu_info_row.pack(fill=tk.X, pady=(0, 8))
        self.cpu_rpm_lbl = tk.Label(cpu_info_row, text="CPU: -- RPM • -- °C", font=("", 13, "bold"), bg=CARD, fg=TEXT)
        self.cpu_rpm_lbl.pack(side=tk.LEFT)
        gpu_info_row = tk.Frame(fan_frame, bg=CARD)
        gpu_info_row.pack(fill=tk.X)
        self.gpu_rpm_lbl = tk.Label(gpu_info_row, text="GPU: -- RPM • -- °C", font=("", 13, "bold"), bg=CARD, fg=TEXT)
        self.gpu_rpm_lbl.pack(side=tk.LEFT)

        # Automático
        auto_frame = _card(content, padx=16, pady=12)
        auto_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(auto_frame, text="AUTOMÁTICO", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 10))
        self.auto_btn = tk.Button(
            auto_frame, text="  Automático  ", font=("", 12, "bold"),
            bg=ACCENT, fg=BG, activebackground=ACCENT_DIM, activeforeground=BG,
            relief=tk.FLAT, padx=24, pady=12, cursor="hand2", command=self._set_auto,
            highlightthickness=0, borderwidth=0,
        )
        self.auto_btn.pack(anchor=tk.W)

        # Cooler Boost
        boost_frame = _card(content, padx=16, pady=12)
        boost_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(boost_frame, text="COOLER BOOST (máximo)", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 10))
        boost_row = tk.Frame(boost_frame, bg=CARD)
        boost_row.pack(fill=tk.X)
        self.cpu_boost_btn = tk.Button(
            boost_row, text="CPU: OFF", font=("", 10, "bold"), bg=BORDER, fg=TEXT,
            relief=tk.FLAT, padx=16, pady=10, cursor="hand2", command=self._toggle_cpu_boost,
            highlightthickness=0, borderwidth=0,
        )
        self.cpu_boost_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.gpu_boost_btn = tk.Button(
            boost_row, text="GPU: OFF", font=("", 10, "bold"), bg=BORDER, fg=TEXT,
            relief=tk.FLAT, padx=16, pady=10, cursor="hand2", command=self._toggle_gpu_boost,
            highlightthickness=0, borderwidth=0,
        )
        self.gpu_boost_btn.pack(side=tk.LEFT)

        # Manual
        manual_frame = _card(content, padx=16, pady=12)
        manual_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(manual_frame, text="MANUAL", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 12))
        tk.Label(manual_frame, text="Defina a velocidade (0-100%) e clique em Aplicar", font=("", 9), bg=CARD, fg=TEXT_MUTED).pack(anchor=tk.W, pady=(0, 10))
        # CPU
        cpu_row = tk.Frame(manual_frame, bg=CARD)
        cpu_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(cpu_row, text="CPU:", font=("", 11), bg=CARD, fg=TEXT, width=6, anchor=tk.W).pack(side=tk.LEFT)
        self.cpu_slider = Slider(cpu_row, from_=0, to=100, value=50, width=200, height=28, bg=CARD)
        self.cpu_slider.pack(side=tk.LEFT, padx=(8, 0))
        # GPU
        gpu_row = tk.Frame(manual_frame, bg=CARD)
        gpu_row.pack(fill=tk.X, pady=(0, 12))
        tk.Label(gpu_row, text="GPU:", font=("", 11), bg=CARD, fg=TEXT, width=6, anchor=tk.W).pack(side=tk.LEFT)
        self.gpu_slider = Slider(gpu_row, from_=0, to=100, value=50, width=200, height=28, bg=CARD)
        self.gpu_slider.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(manual_frame, text="Aplicar ventoinhas", command=self._apply_fans).pack(anchor=tk.W, pady=(8, 0))

    def _toggle_opts(self):
        self._opts_visible = not self._opts_visible
        if self._opts_visible:
            self.opts_panel.pack(fill=tk.X, pady=(0, 8), before=self.content_frame)
        else:
            self.opts_panel.pack_forget()

    def _uninstall(self):
        install_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Só permite desinstalar quando instalado em /usr ou /usr/local
        if not install_dir.startswith("/usr"):
            messagebox.showinfo("Desinstalar", "Executando da pasta do projeto.\nPara desinstalar, execute:\nsudo ./uninstall.sh")
            return
        if not messagebox.askyesno("Desinstalar", "Remover o Acer Nitro 5 Cooler Boost by IB?\n\nO aplicativo será fechado."):
            return
        uninstall_script = os.path.join(install_dir, "uninstall.sh")
        if not os.path.isfile(uninstall_script):
            messagebox.showerror("Desinstalar", "Script de desinstalação não encontrado.\nExecute manualmente: sudo ./uninstall.sh")
            return
        env = os.environ.copy()
        env["INSTALL_DIR"] = install_dir
        try:
            subprocess.run([uninstall_script], env=env, check=True)
            messagebox.showinfo("Desinstalar", "Aplicativo removido com sucesso.")
            self.root.destroy()
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Desinstalar", f"Erro ao desinstalar: {e}")
        except Exception as e:
            messagebox.showerror("Desinstalar", str(e))

    def _check_availability(self):
        ok, msg = self.boost.is_available()
        if ok:
            self.badge.config(text="Pronto", fg=ACCENT)
            fan = self.boost.get_fan_info()
            self._cpu_boost = fan.get("cpu_cooler_boost") or False
            self._gpu_boost = fan.get("gpu_cooler_boost") or False
            self._update_boost_buttons()
        else:
            self.badge.config(text="Erro", fg=DANGER)
            self.auto_btn.config(state=tk.DISABLED)
            self.cpu_boost_btn.config(state=tk.DISABLED)
            self.gpu_boost_btn.config(state=tk.DISABLED)
            messagebox.showerror("Nitro Boost", msg)

    def _set_auto(self):
        if self.boost.set_cooler_boost(False):
            self._cpu_boost = False
            self._gpu_boost = False
            self._update_boost_buttons()
            self.badge.config(text="Automático", fg=ACCENT)
        else:
            messagebox.showerror("Nitro Boost", "Falha ao definir modo automático.")

    def _update_boost_buttons(self):
        if self._cpu_boost:
            self.cpu_boost_btn.config(text="CPU: ON", bg=ACCENT, activebackground=ACCENT_DIM, fg=BG)
        else:
            self.cpu_boost_btn.config(text="CPU: OFF", bg=BORDER, activebackground=BORDER, fg=TEXT)
        if self._gpu_boost:
            self.gpu_boost_btn.config(text="GPU: ON", bg=ACCENT, activebackground=ACCENT_DIM, fg=BG)
        else:
            self.gpu_boost_btn.config(text="GPU: OFF", bg=BORDER, activebackground=BORDER, fg=TEXT)

    def _toggle_cpu_boost(self):
        self._cpu_boost = not self._cpu_boost
        if self.boost.set_cooler_boost_individual(self._cpu_boost, self._gpu_boost):
            self._update_boost_buttons()
            parts = [p for p in ["CPU" if self._cpu_boost else None, "GPU" if self._gpu_boost else None] if p]
            self.badge.config(text=f"Cooler Boost: {', '.join(parts) or 'OFF'}", fg=ACCENT if parts else TEXT_MUTED)
        else:
            self._cpu_boost = not self._cpu_boost
            messagebox.showerror("Nitro Boost", "Falha ao alterar Cooler Boost.")

    def _toggle_gpu_boost(self):
        self._gpu_boost = not self._gpu_boost
        if self.boost.set_cooler_boost_individual(self._cpu_boost, self._gpu_boost):
            self._update_boost_buttons()
            parts = [p for p in ["CPU" if self._cpu_boost else None, "GPU" if self._gpu_boost else None] if p]
            self.badge.config(text=f"Cooler Boost: {', '.join(parts) or 'OFF'}", fg=ACCENT if parts else TEXT_MUTED)
        else:
            self._gpu_boost = not self._gpu_boost
            messagebox.showerror("Nitro Boost", "Falha ao alterar Cooler Boost.")

    def _apply_fans(self):
        cpu_pct = self.cpu_slider.get()
        gpu_pct = self.gpu_slider.get()
        if self.boost.set_custom_fans(cpu_pct, gpu_pct):
            self._cpu_boost = False
            self._gpu_boost = False
            self._update_boost_buttons()
            self.badge.config(text=f"CPU {cpu_pct}% • GPU {gpu_pct}%", fg=ACCENT)
        else:
            messagebox.showerror("Nitro Boost", "Falha ao definir velocidade. Tente modo Automático.")

    def _poll(self):
        # Single instance: verificar se outra instância pediu foco
        focus_file = os.path.expanduser("~/.cache/nitro-boost/focus-request")
        if os.path.isfile(focus_file):
            try:
                os.remove(focus_file)
            except OSError:
                pass
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(100, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()

        ok, _ = self.boost.is_available()
        if not ok:
            return
        fan = self.boost.get_fan_info()
        if fan.get("cpu_cooler_boost") is not None:
            self._cpu_boost = fan["cpu_cooler_boost"]
        if fan.get("gpu_cooler_boost") is not None:
            self._gpu_boost = fan["gpu_cooler_boost"]
        self._update_boost_buttons()

        insights = get_all_insights()
        cpu_rpm = fan.get("cpu_rpm")
        gpu_rpm = fan.get("gpu_rpm")
        if cpu_rpm is None:
            cpu_rpm = insights.get("cpu_fan_rpm")
        if gpu_rpm is None:
            gpu_rpm = insights.get("gpu_fan_rpm")
        cpu_temp = insights.get("cpu", {}).get("temperature")
        gpu_temp = insights.get("gpu_temperature") or (insights.get("gpu") or {}).get("temperature")

        self.cpu_rpm_lbl.config(text=f"CPU: {cpu_rpm or '--'} RPM • {cpu_temp or '--'} °C")
        self.gpu_rpm_lbl.config(text=f"GPU: {gpu_rpm or '--'} RPM • {gpu_temp or '--'} °C")

        if fan.get("mode") == "custom" and fan.get("cpu_percent") is not None and fan.get("gpu_percent") is not None:
            self.cpu_slider.set(fan["cpu_percent"])
            self.gpu_slider.set(fan["gpu_percent"])

        self._poll_id = self.root.after(2000, self._poll)

    def _start_poll(self):
        self.root.after(500, self._poll)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self._poll_id:
            self.root.after_cancel(self._poll_id)
        if hasattr(self, "_lock_fd") and self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except (OSError, AttributeError):
                pass
        self.root.destroy()


def _try_single_instance():
    """Retorna (lock_fd, True) se somos a única instância, ou (None, False) se outra já corre."""
    cache_dir = os.path.expanduser("~/.cache/nitro-boost")
    lock_path = os.path.join(cache_dir, ".lock")
    focus_path = os.path.join(cache_dir, "focus-request")
    os.makedirs(cache_dir, mode=0o700, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, str(os.getpid()).encode())
        return fd, True
    except (OSError, BlockingIOError):
        # Outra instância tem o lock - pedir foco
        try:
            open(focus_path, "w").close()
        except OSError:
            pass
        return None, False


def main():
    if sys.platform != "linux":
        print("Este aplicativo é apenas para Linux/Unix.")
        sys.exit(1)
    import os
    if os.geteuid() != 0:
        for launcher in ["pkexec", "sudo"]:
            try:
                os.execvp(launcher, [launcher] + [sys.executable] + sys.argv)
            except FileNotFoundError:
                continue
        print("Execute com sudo: sudo nitro-boost --gui")
        sys.exit(1)

    lock_fd, is_first = _try_single_instance()
    if not is_first:
        sys.exit(0)  # Outra instância vai receber o foco

    app = NitroBoostApp()
    app._lock_fd = lock_fd
    app.run()


if __name__ == "__main__":
    main()
