import tkinter as tk
from tkinter import messagebox
from urllib import response

import requests

API = "http://127.0.0.1:5000"

# --- Functions ---
def load_students():
    listbox.delete(0, tk.END)
    response = requests.get(f"{API}/api/students")
    students = response.json()
    for s in students:
        listbox.insert(tk.END, f"[{s['rollno']}] {s['name']} | Grade: {s['grade']} | Marks: {s['marks']}")

def search_student():
    query = entry_search.get().strip().lower()
    if not query:
        messagebox.showwarning("Empty", "Enter a name or keyword to search.")
        return

    # Keyword detection
    if query in ["topper", "highest marks", "top student"]:
        url = f"{API}/api/students/topper"
    elif query in ["above avg", "above average"]:
        url = f"{API}/api/students/above-avg"
    elif query in ["below avg", "below average"]:
        url = f"{API}/api/students/below-avg"
    else:
        url = f"{API}/api/students/search?name={query}"

    response = requests.get(url)
    results = response.json()
    listbox.delete(0, tk.END)

    if not results:
        listbox.insert(tk.END, "No student found.")
        return
    for s in results:
        listbox.insert(tk.END, f"[{s['rollno']}] {s['name']} | Grade: {s['grade']} | Marks: {s['marks']}")

def add_student():
    rollno = entry_rollno.get().strip()
    name   = entry_name.get().strip()
    grade  = entry_grade.get().strip()
    marks  = entry_marks.get().strip()

    if not rollno or not name or not grade or not marks:
        messagebox.showwarning("Missing Info", "Please fill in all fields.")
        return

    if not rollno.isdigit():
        messagebox.showerror("Invalid Input", "Roll number must be a whole number.")
        return

    if not marks.isdigit():
        messagebox.showerror("Invalid Input", "Marks must be a whole number, not text.")
        return

    requests.post(f"{API}/api/students", json={
        "rollno": int(rollno),
        "name": name,
        "grade": grade,
        "marks": int(marks)
    })

    entry_rollno.delete(0, tk.END)
    entry_name.delete(0, tk.END)
    entry_grade.delete(0, tk.END)
    entry_marks.delete(0, tk.END)
    load_students()

def delete_student():
    selection = listbox.curselection()
    if not selection:
        messagebox.showwarning("No Selection", "Please select a student from the list first.")
        return
    selected_text = listbox.get(selection[0])
    rollno = int(selected_text.split("]")[0].replace("[", ""))
    requests.delete(f"{API}/api/students/{rollno}")
    load_students()

# --- Window setup ---
root = tk.Tk()
root.title("Classroom Student Manager")
root.geometry("580x520")
root.configure(bg="#1e1e2e")

FONT       = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 11, "bold")
BG         = "#1e1e2e"
FG         = "#cdd6f4"
ACCENT     = "#89b4fa"
ENTRY_BG   = "#313244"
BTN_BG     = "#89b4fa"
BTN_FG     = "#1e1e2e"
LIST_BG    = "#181825"

# --- Title ---
tk.Label(root, text="Classroom Student Manager", font=("Segoe UI", 14, "bold"),
         bg=BG, fg=ACCENT).grid(row=0, column=0, columnspan=3, pady=(16, 10))

# --- Input fields ---
fields = [("Roll No", 1), ("Name", 2), ("Grade", 3), ("Marks", 4)]
entries = {}

for label, row in fields:
    tk.Label(root, text=label, font=FONT, bg=BG, fg=FG).grid(
        row=row, column=0, padx=(20, 8), pady=5, sticky="e")
    e = tk.Entry(root, width=28, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                 relief="flat", font=FONT)
    e.grid(row=row, column=1, pady=5, sticky="w")
    entries[label] = e

entry_rollno = entries["Roll No"]
entry_name   = entries["Name"]
entry_grade  = entries["Grade"]
entry_marks  = entries["Marks"]

tk.Label(root, text="* Marks must be a number", font=("Segoe UI", 8),
         bg=BG, fg="#f38ba8").grid(row=5, column=1, sticky="w")

# --- Add button ---
tk.Button(root, text="Add Student", command=add_student, bg=BTN_BG, fg=BTN_FG,
          font=FONT_BOLD, relief="flat", padx=10, pady=4).grid(
          row=6, column=0, columnspan=2, pady=(10, 4))

# --- Search bar ---
tk.Label(root, text="Search", font=FONT, bg=BG, fg=FG).grid(
    row=7, column=0, padx=(20, 8), pady=5, sticky="e")
entry_search = tk.Entry(root, width=28, bg=ENTRY_BG, fg=FG,
                        insertbackground=FG, relief="flat", font=FONT)
entry_search.grid(row=7, column=1, pady=5, sticky="w")
tk.Button(root, text="Search", command=search_student, bg="#a6e3a1", fg=BTN_FG,
          font=FONT_BOLD, relief="flat", padx=10).grid(row=7, column=2, padx=8)

# --- Listbox ---
tk.Label(root, text="All Students", font=FONT_BOLD, bg=BG, fg=ACCENT).grid(
    row=8, column=0, columnspan=3, pady=(12, 2))
listbox = tk.Listbox(root, width=65, height=10, bg=LIST_BG, fg=FG,
                     selectbackground=ACCENT, selectforeground=BTN_FG,
                     font=FONT, relief="flat", borderwidth=0)
listbox.grid(row=9, column=0, columnspan=3, padx=20, pady=4)

# --- Bottom buttons ---
btn_frame = tk.Frame(root, bg=BG)
btn_frame.grid(row=10, column=0, columnspan=3, pady=10)

tk.Button(btn_frame, text="Refresh", command=load_students, bg=ENTRY_BG,
          fg=FG, font=FONT, relief="flat", padx=10).pack(side="left", padx=8)
tk.Button(btn_frame, text="Delete Selected", command=delete_student,
          bg="#f38ba8", fg=BTN_FG, font=FONT_BOLD, relief="flat", padx=10).pack(side="left", padx=8)

load_students()
root.mainloop()