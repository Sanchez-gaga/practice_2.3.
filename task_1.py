import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import time
import urllib.request
import urllib.error
import sys
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Фолбэк-функции (упрощённые) без psutil
    def get_cpu_percent():
        return 0
    def get_memory():
        return (0, 0, 0)
    def get_disk_usage(path):
        return (0, 0, 0)
    

CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
SAVE_FILE = "currency_groups.json"

def load_groups():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_groups(groups):
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, indent=4, ensure_ascii=False)

def fetch_rates():
    try:
        req = urllib.request.Request(CBR_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['Valute']
    except Exception:
        return None

GITHUB_API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"

def github_request(url, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "Python-GitHub-Client"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

def get_github_profile(username, token=None):
    url = f"{GITHUB_API_URL}/users/{username}"
    data = github_request(url, token)
    if not data or "message" in data:
        return None
    return data

def get_github_repos(username, token=None):
    url = f"{GITHUB_API_URL}/users/{username}/repos?per_page=100"
    data = github_request(url, token)
    if not data or (isinstance(data, dict) and "message" in data):
        return None
    return data

def search_github_repos(query, token=None):
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"{GITHUB_API_URL}/search/repositories?q={encoded}&per_page=10"
    data = github_request(url, token)
    if not data or "message" in data:
        return None
    return data.get('items', [])

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Мульти-инструмент")
        self.root.geometry("900x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        
        self.currency_groups = load_groups()
        self.rates = None

        
        self.github_token = None

        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        
        self.frame_system = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_system, text="Системный монитор")
        self.setup_system_tab()

        
        self.frame_currency = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_currency, text="Курсы валют")
        self.setup_currency_tab()

        
        self.frame_github = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_github, text="GitHub")
        self.setup_github_tab()

        
        if PSUTIL_AVAILABLE:
            self.update_system_info()
        else:
            self.system_text.insert(tk.END, "Библиотека psutil не установлена. Установите её для работы монитора.\n")

        
        self.refresh_currency_rates()

    def on_close(self):
        
        save_groups(self.currency_groups)
        self.root.destroy()

    def setup_system_tab(self):
        self.system_text = scrolledtext.ScrolledText(self.frame_system, wrap=tk.WORD, width=80, height=30)
        self.system_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        if not PSUTIL_AVAILABLE:
            self.system_text.insert(tk.END, "Для работы системного монитора требуется установить psutil.\n")
            self.system_text.insert(tk.END, "Выполните: pip install psutil\n")

    def update_system_info(self):
        if PSUTIL_AVAILABLE:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            info = f"--- {datetime.now().strftime('%H:%M:%S')} ---\n"
            info += f"CPU загрузка: {cpu}%\n"
            info += f"RAM: использовано {mem.used / (1024**3):.1f} ГБ из {mem.total / (1024**3):.1f} ГБ ({mem.percent}%)\n"
            info += f"Диск: использовано {disk.used / (1024**3):.1f} ГБ из {disk.total / (1024**3):.1f} ГБ ({disk.percent}%)\n"
            info += "-" * 40 + "\n"
            self.system_text.insert(tk.END, info)
            self.system_text.see(tk.END)
        self.root.after(2000, self.update_system_info)

    def setup_currency_tab(self):
        # Верхняя панель: кнопки и поля
        top_frame = ttk.Frame(self.frame_currency)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(top_frame, text="Обновить курсы", command=self.refresh_currency_rates).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Все курсы", command=self.show_all_rates).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Группы", command=self.manage_groups).pack(side=tk.LEFT, padx=5)

        ttk.Label(top_frame, text="Код валюты:").pack(side=tk.LEFT, padx=(20,5))
        self.currency_code_entry = ttk.Entry(top_frame, width=10)
        self.currency_code_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Показать курс", command=self.show_single_rate).pack(side=tk.LEFT, padx=5)

        
        self.currency_text = scrolledtext.ScrolledText(self.frame_currency, wrap=tk.WORD, width=80, height=25)
        self.currency_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def refresh_currency_rates(self):
        self.currency_text.insert(tk.END, "Загрузка курсов...\n")
        self.currency_text.see(tk.END)
        
        threading.Thread(target=self._fetch_rates_thread, daemon=True).start()

    def _fetch_rates_thread(self):
        rates = fetch_rates()
        self.rates = rates
        self.root.after(0, self._update_currency_display, "Курсы загружены.\n")

    def _update_currency_display(self, msg):
        self.currency_text.insert(tk.END, msg)
        self.currency_text.see(tk.END)

    def show_all_rates(self):
        if not self.rates:
            self.currency_text.insert(tk.END, "Нет данных. Нажмите 'Обновить курсы'.\n")
            return
        self.currency_text.delete(1.0, tk.END)
        self.currency_text.insert(tk.END, "=== КУРСЫ ВАЛЮТ ===\n")
        for code, info in sorted(self.rates.items()):
            self.currency_text.insert(tk.END, f"{code} ({info['Name']}): {info['Value']:.4f} руб.\n")
        self.currency_text.see(tk.END)

    def show_single_rate(self):
        if not self.rates:
            self.currency_text.insert(tk.END, "Нет данных. Обновите курсы.\n")
            return
        code = self.currency_code_entry.get().strip().upper()
        if not code:
            self.currency_text.insert(tk.END, "Введите код валюты.\n")
            return
        if code in self.rates:
            info = self.rates[code]
            self.currency_text.insert(tk.END, f"{code} ({info['Name']}): {info['Value']:.4f} руб.\n")
        else:
            self.currency_text.insert(tk.END, f"Валюта {code} не найдена.\n")
        self.currency_text.see(tk.END)

    def manage_groups(self):
        
        win = tk.Toplevel(self.root)
        win.title("Управление группами валют")
        win.geometry("600x500")

        
        listbox = tk.Listbox(win)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        
        def refresh_list():
            listbox.delete(0, tk.END)
            for name in self.currency_groups:
                listbox.insert(tk.END, name)

        refresh_list()

        
        btn_frame = ttk.Frame(win)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        def add_group():
            name = tk.simpledialog.askstring("Новая группа", "Введите название группы:")
            if name and name not in self.currency_groups:
                codes = tk.simpledialog.askstring("Валюты", "Введите коды валют через пробел (например, USD EUR):")
                if codes is not None:
                    self.currency_groups[name] = codes.strip().upper().split()
                    save_groups(self.currency_groups)
                    refresh_list()
            else:
                messagebox.showerror("Ошибка", "Группа уже существует или имя пустое")

        def edit_group():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0])
            
            codes = self.currency_groups.get(name, [])
            new_codes_str = tk.simpledialog.askstring("Редактирование", "Введите коды валют через пробел:", initialvalue=" ".join(codes))
            if new_codes_str is not None:
                self.currency_groups[name] = new_codes_str.strip().upper().split()
                save_groups(self.currency_groups)
                refresh_list()

        def delete_group():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0])
            if messagebox.askyesno("Удаление", f"Удалить группу '{name}'?"):
                del self.currency_groups[name]
                save_groups(self.currency_groups)
                refresh_list()

        def view_group():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0])
            codes = self.currency_groups.get(name, [])
            if not self.rates:
                messagebox.showinfo("Инфо", "Сначала обновите курсы валют.")
                return
            text = f"Группа '{name}':\n"
            for code in codes:
                if code in self.rates:
                    info = self.rates[code]
                    text += f"{code} ({info['Name']}): {info['Value']:.4f} руб.\n"
                else:
                    text += f"{code}: не найдена\n"
            messagebox.showinfo("Курсы группы", text)

        ttk.Button(btn_frame, text="Создать", command=add_group).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Редактировать", command=edit_group).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Удалить", command=delete_group).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Просмотреть", command=view_group).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Закрыть", command=win.destroy).pack(fill=tk.X, pady=2)

    def setup_github_tab(self):
        
        token_frame = ttk.Frame(self.frame_github)
        token_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(token_frame, text="GitHub Token (опционально):").pack(side=tk.LEFT)
        self.token_entry = ttk.Entry(token_frame, width=40, show="*")
        self.token_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(token_frame, text="Установить", command=self.set_github_token).pack(side=tk.LEFT)

        
        user_frame = ttk.LabelFrame(self.frame_github, text="Профиль пользователя")
        user_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(user_frame, text="Имя пользователя:").pack(side=tk.LEFT, padx=5)
        self.user_entry = ttk.Entry(user_frame, width=30)
        self.user_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(user_frame, text="Показать профиль", command=self.show_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(user_frame, text="Репозитории", command=self.show_repos).pack(side=tk.LEFT, padx=5)

        
        search_frame = ttk.LabelFrame(self.frame_github, text="Поиск репозиториев")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(search_frame, text="Поисковый запрос:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Искать", command=self.search_repos).pack(side=tk.LEFT, padx=5)

        
        self.github_text = scrolledtext.ScrolledText(self.frame_github, wrap=tk.WORD, width=80, height=25)
        self.github_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def set_github_token(self):
        token = self.token_entry.get().strip()
        if token:
            self.github_token = token
            self.github_text.insert(tk.END, "Токен установлен.\n")
        else:
            self.github_token = None
            self.github_text.insert(tk.END, "Токен удалён.\n")
        self.github_text.see(tk.END)

    def show_profile(self):
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showerror("Ошибка", "Введите имя пользователя")
            return
        self.github_text.insert(tk.END, f"Загрузка профиля {username}...\n")
        threading.Thread(target=self._fetch_profile_thread, args=(username,), daemon=True).start()

    def _fetch_profile_thread(self, username):
        data = get_github_profile(username, self.github_token)
        self.root.after(0, self._display_profile, data, username)

    def _display_profile(self, data, username):
        if not data:
            self.github_text.insert(tk.END, f"Не удалось получить профиль {username}.\n")
            self.github_text.see(tk.END)
            return
        if "message" in data:
            self.github_text.insert(tk.END, f"Ошибка: {data['message']}\n")
            self.github_text.see(tk.END)
            return
        text = f"=== ПРОФИЛЬ {username} ===\n"
        text += f"Имя: {data.get('name', 'не указано')}\n"
        text += f"Ссылка: {data.get('html_url', 'нет')}\n"
        text += f"Публичные репозитории: {data.get('public_repos', 0)}\n"
        text += f"Gists: {data.get('public_gists', 0)}\n"
        text += f"Подписчики: {data.get('followers', 0)}\n"
        text += f"Подписки: {data.get('following', 0)}\n"
        self.github_text.insert(tk.END, text + "\n")
        self.github_text.see(tk.END)

    def show_repos(self):
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showerror("Ошибка", "Введите имя пользователя")
            return
        self.github_text.insert(tk.END, f"Загрузка репозиториев {username}...\n")
        threading.Thread(target=self._fetch_repos_thread, args=(username,), daemon=True).start()
    def _fetch_repos_thread(self, username): 
        repos = get_github_repos(username, self.github_token)
    
        self.root.after(0, self._display_repos, repos, username)

    def _display_repos(self, repos, username):
        if repos is None:
            self.github_text.insert(tk.END, f"Не удалось получить репозитории {username}.\n")
            self.github_text.see(tk.END)
            return
        if isinstance(repos, dict) and "message" in repos:
            self.github_text.insert(tk.END, f"Ошибка: {repos['message']}\n")
            self.github_text.see(tk.END)
            return
        if not repos:
            self.github_text.insert(tk.END, f"У {username} нет публичных репозиториев.\n")
            return
        text = f"=== РЕПОЗИТОРИИ {username} ===\n"
        for repo in repos:
            name = repo.get('name')
            url = repo.get('html_url')
            lang = repo.get('language', 'не указан')
            private = "приватный" if repo.get('private') else "публичный"
            branch = repo.get('default_branch')
            text += f"\nНазвание: {name}\nСсылка: {url}\nЯзык: {lang}\nВидимость: {private}\nВетка по умолчанию: {branch}\n"
            text += "-" * 40 + "\n"
        self.github_text.insert(tk.END, text)
        self.github_text.see(tk.END)

    def search_repos(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showerror("Ошибка", "Введите поисковый запрос")
            return
        self.github_text.insert(tk.END, f"Поиск репозиториев по запросу '{query}'...\n")
        threading.Thread(target=self._search_repos_thread, args=(query,), daemon=True).start()

    def _search_repos_thread(self, query):
        items = search_github_repos(query, self.github_token)
        self.root.after(0, self._display_search, items, query)

    def _display_search(self, items, query):
        if items is None:
            self.github_text.insert(tk.END, f"Ошибка при поиске.\n")
            return
        if not items:
            self.github_text.insert(tk.END, f"Ничего не найдено по запросу '{query}'.\n")
            return
        text = f"=== РЕЗУЛЬТАТЫ ПОИСКА: {query} ===\nНайдено {len(items)} репозиториев:\n\n"
        for repo in items:
            name = repo.get('full_name')
            url = repo.get('html_url')
            lang = repo.get('language', 'не указан')
            private = "приватный" if repo.get('private') else "публичный"
            text += f"Название: {name}\nСсылка: {url}\nЯзык: {lang}\nВидимость: {private}\n"
            text += "-" * 40 + "\n"
        self.github_text.insert(tk.END, text)
        self.github_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()