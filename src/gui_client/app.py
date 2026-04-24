from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from .claude_client import request_analysis


def _format_result(payload: dict) -> str:
    lines = [
        f"Stock {payload.get('stock_code')} | horizon {payload.get('horizon_days')}d",
        f"As of {payload.get('as_of')} | last close JPY {payload.get('last_close')}",
        "",
        "Summary:",
        payload.get("summary", ""),
        "",
        f"{'Scenario':<8}{'Price (JPY)':>14}{'Prob':>8}",
        "-" * 30,
    ]
    for name in ("bear", "base", "bull"):
        sc = payload.get(name) or {}
        price = sc.get("price", "?")
        prob = sc.get("probability", "?")
        lines.append(f"{name:<8}{price:>14}{prob:>8}")
    lines.append("")
    for name in ("bear", "base", "bull"):
        sc = payload.get(name) or {}
        lines.append(f"[{name}] {sc.get('rationale', '')}")
        lines.append("")
    lines.append(payload.get("disclaimer", ""))
    return "\n".join(lines)


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("SmartTools — JP Stock Analyst")
        root.geometry("760x560")

        frm = ttk.Frame(root, padding=10)
        frm.pack(fill="x")

        ttk.Label(frm, text="TSE code (e.g. 7203):").grid(row=0, column=0, sticky="w")
        self.code_var = tk.StringVar(value="7203")
        ttk.Entry(frm, textvariable=self.code_var, width=12).grid(row=0, column=1, padx=6)

        ttk.Label(frm, text="Horizon (days):").grid(row=0, column=2, sticky="w")
        self.days_var = tk.StringVar(value="30")
        ttk.Entry(frm, textvariable=self.days_var, width=8).grid(row=0, column=3, padx=6)

        self.run_btn = ttk.Button(frm, text="Analyze", command=self._on_run)
        self.run_btn.grid(row=0, column=4, padx=12)

        self.text = scrolledtext.ScrolledText(root, wrap="word", font=("Consolas", 10))
        self.text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status, anchor="w", relief="sunken").pack(fill="x")

    def _on_run(self) -> None:
        code = self.code_var.get().strip()
        try:
            days = int(self.days_var.get().strip())
        except ValueError:
            self.status.set("Days must be an integer.")
            return
        if not code.isdigit():
            self.status.set("Stock code must be numeric (e.g. 7203).")
            return

        self.run_btn.state(["disabled"])
        self.status.set(f"Asking Claude to analyze {code} over {days} days…")
        self.text.delete("1.0", "end")
        threading.Thread(target=self._do_call, args=(code, days), daemon=True).start()

    def _do_call(self, code: str, days: int) -> None:
        try:
            payload = request_analysis(code, days)
            self.root.after(0, self._on_success, payload)
        except Exception as e:  # noqa: BLE001
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, payload: dict) -> None:
        self.text.insert("1.0", _format_result(payload))
        self.text.insert("end", "\n\n--- raw JSON ---\n" + json.dumps(payload, indent=2))
        self.status.set("Done.")
        self.run_btn.state(["!disabled"])

    def _on_error(self, msg: str) -> None:
        self.text.insert("1.0", f"ERROR: {msg}")
        self.status.set("Failed.")
        self.run_btn.state(["!disabled"])


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
