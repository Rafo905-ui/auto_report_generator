#!/usr/bin/env python3
"""Tkinter GUI to switch sources and control cameras on a Blackmagic ATEM switcher."""

import argparse
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import PyATEMMax

DEFAULT_IP = "192.168.1.240"
CONNECT_TIMEOUT = 10.0
REFRESH_MS = 500
SLIDER_DEBOUNCE_MS = 120
MAX_INPUTS = 20
MAX_CAMERAS = 8
IRIS_MAX = 2048
FOCUS_MAX = 65535
GAIN_VALUES = (512, 1024, 2048, 4096)
WHITE_BALANCE_VALUES = (3200, 4500, 5000, 5600, 6500, 7500)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATEM switcher control GUI.")
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"ATEM IP (default: {DEFAULT_IP})")
    parser.add_argument("--me", type=int, default=0, help="Mix effect block (default: 0)")
    return parser.parse_args()


class ATEMGui:
    def __init__(self, root: tk.Tk, ip: str, me: int) -> None:
        self.root = root
        self.me = me
        self.switcher = PyATEMMax.ATEMMax()
        self.ip_var = tk.StringVar(value=ip)
        self.status_var = tk.StringVar(value="Not connected")
        self.model_var = tk.StringVar(value="-")
        self.program_var = tk.StringVar(value="-")
        self.preview_var = tk.StringVar(value="-")
        self.camera_var = tk.IntVar(value=1)
        self.iris_var = tk.IntVar(value=0)
        self.focus_var = tk.IntVar(value=0)
        self.program_buttons: dict[int, ttk.Button] = {}
        self.preview_buttons: dict[int, ttk.Button] = {}
        self.pending_iris: str | None = None
        self.pending_focus: str | None = None

        root.title("ATEM control")
        self._build_connection_frame()
        self._build_source_frame()
        self._build_transition_frame()
        self._build_camera_frame()
        self._build_status_frame()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(REFRESH_MS, self.refresh_state)

    def _build_connection_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Connection")
        frame.pack(fill="x", padx=8, pady=6)
        ttk.Label(frame, text="IP:").pack(side="left", padx=(8, 4), pady=6)
        ttk.Entry(frame, textvariable=self.ip_var, width=16).pack(side="left", pady=6)
        self.connect_button = ttk.Button(frame, text="Connect", command=self.connect)
        self.connect_button.pack(side="left", padx=6, pady=6)
        self.disconnect_button = ttk.Button(
            frame, text="Disconnect", command=self.disconnect, state="disabled"
        )
        self.disconnect_button.pack(side="left", padx=(0, 8), pady=6)
        ttk.Label(frame, textvariable=self.model_var).pack(side="left", padx=8)

    def _build_source_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text=f"Sources (M/E {self.me})")
        frame.pack(fill="x", padx=8, pady=6)

        ttk.Label(frame, text="Program").grid(row=0, column=0, padx=8, pady=(6, 2), sticky="w")
        ttk.Label(frame, text="Preview").grid(row=1, column=0, padx=8, pady=(2, 6), sticky="w")
        for index in range(1, MAX_INPUTS + 1):
            program_button = ttk.Button(
                frame,
                text=str(index),
                width=4,
                command=lambda source=index: self.set_program(source),
            )
            program_button.grid(row=0, column=index, padx=2, pady=(6, 2))
            self.program_buttons[index] = program_button

            preview_button = ttk.Button(
                frame,
                text=str(index),
                width=4,
                command=lambda source=index: self.set_preview(source),
            )
            preview_button.grid(row=1, column=index, padx=2, pady=(2, 6))
            self.preview_buttons[index] = preview_button

    def _build_transition_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Transition")
        frame.pack(fill="x", padx=8, pady=6)
        ttk.Button(frame, text="CUT", width=10, command=self.do_cut).pack(
            side="left", padx=8, pady=6
        )
        ttk.Button(frame, text="AUTO", width=10, command=self.do_auto).pack(
            side="left", padx=8, pady=6
        )
        ttk.Label(frame, text="Program:").pack(side="left", padx=(16, 2))
        ttk.Label(frame, textvariable=self.program_var, width=12).pack(side="left")
        ttk.Label(frame, text="Preview:").pack(side="left", padx=(8, 2))
        ttk.Label(frame, textvariable=self.preview_var, width=12).pack(side="left")

    def _build_camera_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Camera control")
        frame.pack(fill="both", expand=True, padx=8, pady=6)

        ttk.Label(frame, text="Camera:").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.camera_var,
            values=list(range(1, MAX_CAMERAS + 1)),
            width=4,
            state="readonly",
        ).grid(row=0, column=1, pady=6, sticky="w")
        ttk.Button(frame, text="Auto focus", command=self.do_auto_focus).grid(
            row=0, column=2, padx=8, pady=6
        )
        ttk.Button(frame, text="Auto iris", command=self.do_auto_iris).grid(
            row=0, column=3, padx=8, pady=6
        )

        ttk.Label(frame, text="Iris").grid(row=1, column=0, padx=8, sticky="w")
        ttk.Scale(
            frame,
            from_=0,
            to=IRIS_MAX,
            orient="horizontal",
            length=280,
            command=self.on_iris_change,
        ).grid(row=1, column=1, columnspan=3, sticky="we", padx=8, pady=4)
        ttk.Label(frame, textvariable=self.iris_var, width=6).grid(row=1, column=4, padx=8)

        ttk.Label(frame, text="Focus").grid(row=2, column=0, padx=8, sticky="w")
        ttk.Scale(
            frame,
            from_=0,
            to=FOCUS_MAX,
            orient="horizontal",
            length=280,
            command=self.on_focus_change,
        ).grid(row=2, column=1, columnspan=3, sticky="we", padx=8, pady=4)
        ttk.Label(frame, textvariable=self.focus_var, width=6).grid(row=2, column=4, padx=8)

        ttk.Label(frame, text="Gain").grid(row=3, column=0, padx=8, sticky="w")
        gain_frame = ttk.Frame(frame)
        gain_frame.grid(row=3, column=1, columnspan=4, sticky="w", pady=4)
        for gain in GAIN_VALUES:
            ttk.Button(
                gain_frame,
                text=str(gain),
                width=6,
                command=lambda value=gain: self.set_gain(value),
            ).pack(side="left", padx=2)

        ttk.Label(frame, text="White balance").grid(row=4, column=0, padx=8, sticky="w")
        wb_frame = ttk.Frame(frame)
        wb_frame.grid(row=4, column=1, columnspan=4, sticky="w", pady=(4, 8))
        for kelvin in WHITE_BALANCE_VALUES:
            ttk.Button(
                wb_frame,
                text=f"{kelvin}K",
                width=6,
                command=lambda value=kelvin: self.set_white_balance(value),
            ).pack(side="left", padx=2)

    def _build_status_frame(self) -> None:
        ttk.Label(self.root, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=8, pady=(0, 8)
        )

    def connect(self) -> None:
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showerror("ATEM control", "Enter the switcher IP address")
            return
        self.connect_button.config(state="disabled")
        self.status_var.set(f"Connecting to {ip} ...")
        threading.Thread(target=self._connect_worker, args=(ip,), daemon=True).start()

    def _connect_worker(self, ip: str) -> None:
        self.switcher.connect(ip)
        connected = self.switcher.waitForConnection(infinite=False, timeout=CONNECT_TIMEOUT)
        self.root.after(0, lambda: self._connect_done(ip, connected))

    def _connect_done(self, ip: str, connected: bool) -> None:
        if connected:
            self.status_var.set(f"Connected to {ip}")
            self.model_var.set(f"{self.switcher.atemModel} ({self.switcher.videoMode.format})")
            self.disconnect_button.config(state="normal")
        else:
            self.switcher.disconnect()
            self.status_var.set(f"Failed to connect to {ip}")
            self.connect_button.config(state="normal")

    def disconnect(self) -> None:
        self.switcher.disconnect()
        self.status_var.set("Disconnected")
        self.model_var.set("-")
        self.program_var.set("-")
        self.preview_var.set("-")
        self.connect_button.config(state="normal")
        self.disconnect_button.config(state="disabled")

    def require_connection(self) -> bool:
        if self.switcher.connected:
            return True
        self.status_var.set("Not connected")
        return False

    def set_program(self, source: int) -> None:
        if self.require_connection():
            self.switcher.setProgramInputVideoSource(self.me, source)
            self.status_var.set(f"Program -> input {source}")

    def set_preview(self, source: int) -> None:
        if self.require_connection():
            self.switcher.setPreviewInputVideoSource(self.me, source)
            self.status_var.set(f"Preview -> input {source}")

    def do_cut(self) -> None:
        if self.require_connection():
            self.switcher.execCutME(self.me)
            self.status_var.set("Cut")

    def do_auto(self) -> None:
        if self.require_connection():
            self.switcher.execAutoME(self.me)
            self.status_var.set("Auto transition")

    def do_auto_focus(self) -> None:
        if self.require_connection():
            self.switcher.setCameraControlAutoFocus(self.camera_var.get())
            self.status_var.set(f"Camera {self.camera_var.get()}: auto focus")

    def do_auto_iris(self) -> None:
        if self.require_connection():
            self.switcher.setCameraControlAutoIris(self.camera_var.get())
            self.status_var.set(f"Camera {self.camera_var.get()}: auto iris")

    def on_iris_change(self, value: str) -> None:
        self.iris_var.set(int(float(value)))
        if self.pending_iris is not None:
            self.root.after_cancel(self.pending_iris)
        self.pending_iris = self.root.after(SLIDER_DEBOUNCE_MS, self.send_iris)

    def send_iris(self) -> None:
        self.pending_iris = None
        iris = self.iris_var.get()
        if self.switcher.connected:
            self.switcher.setCameraControlIris(self.camera_var.get(), iris)
            self.status_var.set(f"Camera {self.camera_var.get()}: iris {iris}")

    def on_focus_change(self, value: str) -> None:
        self.focus_var.set(int(float(value)))
        if self.pending_focus is not None:
            self.root.after_cancel(self.pending_focus)
        self.pending_focus = self.root.after(SLIDER_DEBOUNCE_MS, self.send_focus)

    def send_focus(self) -> None:
        self.pending_focus = None
        focus = self.focus_var.get()
        if self.switcher.connected:
            self.switcher.setCameraControlFocus(self.camera_var.get(), focus)
            self.status_var.set(f"Camera {self.camera_var.get()}: focus {focus}")

    def set_gain(self, gain: int) -> None:
        if self.require_connection():
            self.switcher.setCameraControlGain(self.camera_var.get(), gain)
            self.status_var.set(f"Camera {self.camera_var.get()}: gain {gain}")

    def set_white_balance(self, kelvin: int) -> None:
        if self.require_connection():
            self.switcher.setCameraControlWhiteBalance(self.camera_var.get(), kelvin)
            self.status_var.set(f"Camera {self.camera_var.get()}: white balance {kelvin}K")

    def refresh_state(self) -> None:
        if self.switcher.connected:
            program = self.switcher.programInput[self.me].videoSource
            preview = self.switcher.previewInput[self.me].videoSource
            self.program_var.set(str(program))
            self.preview_var.set(str(preview))
            self._highlight(self.program_buttons, program)
            self._highlight(self.preview_buttons, preview)
            for index, button in self.program_buttons.items():
                name = self.switcher.inputProperties[index].shortName
                state = "normal" if name else "disabled"
                button.config(text=name if name else str(index), state=state)
                self.preview_buttons[index].config(
                    text=name if name else str(index), state=state
                )
        self.root.after(REFRESH_MS, self.refresh_state)

    def _highlight(self, buttons: dict[int, ttk.Button], active: object) -> None:
        active_name = str(active)
        for index, button in buttons.items():
            is_active = active_name in (f"input{index}", str(index))
            button.state(["pressed"] if is_active else ["!pressed"])

    def on_close(self) -> None:
        self.switcher.disconnect()
        self.root.destroy()


def main() -> int:
    args = parse_args()
    root = tk.Tk()
    ATEMGui(root, args.ip, args.me)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
