import tkinter as tk
from tkinter import ttk


def on_button_click():
    name = name_entry.get()
    greeting = f"Hello, {name}!" if name else "Hello, World!"
    label_result.config(text=greeting)


root = tk.Tk()
root.title("My Tkinter App")
root.geometry("400x300")
root.resizable(True, True)

main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(main_frame, text="Enter your name:").pack(anchor=tk.W)

name_entry = ttk.Entry(main_frame, width=30)
name_entry.pack(fill=tk.X, pady=(4, 12))

ttk.Button(main_frame, text="Greet", command=on_button_click).pack()

label_result = ttk.Label(main_frame, text="", font=("TkDefaultFont", 14))
label_result.pack(pady=16)

root.mainloop()
