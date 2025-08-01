import tkinter as tk
from tkinter import ttk

def update_sub_combobox(event):
    selected_category = main_combobox_var.get()
    if selected_category == "Fruits":
        sub_combobox['values'] = ["Apple", "Banana", "Cherry"]
    elif selected_category == "Vegetables":
        sub_combobox['values'] = ["Carrot", "Spinach", "Broccoli"]
    else:
        sub_combobox['values'] = [] # Clear if no category selected

root = tk.Tk()
root.title("Linked Comboboxes")

main_combobox_var = tk.StringVar()
main_combobox = ttk.Combobox(root, textvariable=main_combobox_var, values=["Fruits", "Vegetables"])
main_combobox.pack(pady=10)
main_combobox.bind("<<ComboboxSelected>>", update_sub_combobox)

sub_combobox_var = tk.StringVar()
sub_combobox = ttk.Combobox(root, textvariable=sub_combobox_var)
sub_combobox.pack(pady=10)

root.mainloop()