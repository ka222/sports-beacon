import os
import sqlite3
import uuid
import hashlib
import math
from datetime import datetime, timedelta

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

DB_NAME = "sports_beacon.db"

# --- COASTAL DISTANCE DATA & CALCULATION ---
COASTAL_COORDS = {
    "brighton": (50.8225, -0.1372),
    "worthing": (50.8179, -0.3727),
    "eastbourne": (50.7680, 0.2838),
    "hastings": (50.8552, 0.5729),
    "bexhill": (50.8422, 0.4678),
    "shoreham": (50.8335, -0.2721),
    "littlehampton": (50.8093, -0.5409),
    "bognor regis": (50.7831, -0.6778),
    "seaford": (50.7714, 0.1026),
    "lewes": (50.8741, 0.0077),
}

def get_coastal_distance(town1: str, town2: str):
    t1 = str(town1 or "").strip().lower()
    t2 = str(town2 or "").strip().lower()
    if t1 == t2:
        return 0.0
    if t1 not in COASTAL_COORDS or t2 not in COASTAL_COORDS:
        return None

    lat1, lon1 = COASTAL_COORDS[t1]
    lat2, lon2 = COASTAL_COORDS[t2]

    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

# --- SECURITY HELPERS ---
def ensure_bytes(val) -> bytes:
    if isinstance(val, str):
        return val.encode('utf-8')
    return val

def hash_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    salt = ensure_bytes(salt)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key, salt

def verify_password(password: str, stored_key, salt) -> bool:
    try:
        stored_key = ensure_bytes(stored_key)
        salt = ensure_bytes(salt)
        computed_key, _ = hash_password(password, salt)
        return computed_key == stored_key
    except Exception:
        return False

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash BLOB NOT NULL,
        salt BLOB NOT NULL,
        name TEXT NOT NULL,
        location TEXT,
        sport TEXT,
        skill_level TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        host_id TEXT NOT NULL,
        sport TEXT NOT NULL,
        location TEXT NOT NULL,
        skill_level TEXT NOT NULL,
        match_date TEXT NOT NULL DEFAULT '',
        match_time TEXT NOT NULL DEFAULT '',
        venue TEXT NOT NULL DEFAULT '',
        max_players INTEGER NOT NULL DEFAULT 4,
        status TEXT DEFAULT 'OPEN',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (host_id) REFERENCES users (id) ON DELETE CASCADE
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_players (
        match_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (match_id, user_id),
        FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS direct_messages (
        id TEXT PRIMARY KEY,
        sender_id TEXT NOT NULL,
        receiver_id TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
    )""")

    conn.commit()
    conn.close()

init_db()
current_user = None

def get_upcoming_reminders(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.sport, m.location, m.venue, m.match_date, m.match_time
    FROM matches m
    JOIN match_players mp ON m.id = mp.match_id
    WHERE mp.user_id = ? AND m.status = 'OPEN'
    """, (user_id,))

    upcoming = []
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    for sport, location, venue, date_str, time_str in cursor.fetchall():
        try:
            match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if match_date == today:
                upcoming.append((sport, venue or location, f"Today at {time_str}"))
            elif match_date == tomorrow:
                upcoming.append((sport, venue or location, f"Tomorrow at {time_str}"))
        except ValueError:
            continue

    conn.close()
    return upcoming

# --- CUSTOM UI COMPONENTS ---
class OvalButton(Button):
    def __init__(self, text="", on_press_callback=None, bg_color=(0, 0.4, 0.4, 1), text_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.font_size = "14sp"
        self.bold = True
        self.color = text_color
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ""
        self.size_hint_y = None
        self.height = "42dp"

        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
        self.bind(size=self._update_rect, pos=self._update_rect)

        if on_press_callback:
            self.bind(on_release=on_press_callback)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

class MatchCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [12, 12, 12, 12]
        self.spacing = 6
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        with self.canvas.before:
            Color(0.18, 0.22, 0.25, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

# --- MAIN APPLICATION ---
class SportsBeaconApp(App):
    poll_event = None
    cards_dict = {}

    current_search_query = ""
    current_date_query = ""
    current_venue_query = ""

    def show_dialog(self, title, message):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(text=message, halign='center', color=(0.9, 0.9, 0.9, 1)))
        btn = OvalButton(text="OK", bg_color=(0, 0.5, 0.5, 1))
        content.add_widget(btn)
        
        popup = Popup(title=title, content=content, size_hint=(0.85, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def clear_login_fields(self, instance=None):
        self.login_email.text = ""
        self.login_pass.text = ""

    def build(self):
        self.sm = ScreenManager()

        # LOGIN SCREEN
        login_screen = Screen(name="login")
        layout = BoxLayout(orientation="vertical", spacing=12, padding=24)
        layout.add_widget(Widget(size_hint_y=1))

        layout.add_widget(Label(text="SPORTS BEACON", font_size="26sp", bold=True, color=(0, 0.6, 0.6, 1), size_hint_y=None, height=40))
        layout.add_widget(Label(text="Coastal Matchmaking Platform", font_size="14sp", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=25))

        self.login_email = TextInput(
            hint_text="Email Address",
            multiline=False,
            size_hint_y=None,
            height=48,
            write_tab=False,
            input_type='mail'
        )
        self.login_pass = TextInput(
            hint_text="Password",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=48,
            write_tab=False
        )
        
        clear_btn = OvalButton(
            text="Clear Input Fields", 
            on_press_callback=self.clear_login_fields, 
            bg_color=(0.3, 0.3, 0.3, 1),
            size_hint_y=None,
            height=36
        )

        login_btn = OvalButton(text="LOG IN", on_press_callback=self.verify_login)
        signup_redirect_btn = OvalButton(text="Create an Account", on_press_callback=lambda x: setattr(self.sm, 'current', 'signup'), bg_color=(0.2, 0.2, 0.2, 1))

        layout.add_widget(self.login_email)
        layout.add_widget(self.login_pass)
        layout.add_widget(clear_btn)
        layout.add_widget(login_btn)
        layout.add_widget(signup_redirect_btn)
        layout.add_widget(Widget(size_hint_y=1))
        
        login_screen.add_widget(layout)
        self.sm.add_widget(login_screen)

        # SIGNUP SCREEN
        signup_screen = Screen(name="signup")
        signup_scroll = ScrollView()
        signup_layout = BoxLayout(orientation="vertical", spacing=10, padding=20, size_hint_y=None)
        signup_layout.bind(minimum_height=signup_layout.setter("height"))

        signup_layout.add_widget(Label(text="Create Account", font_size="22sp", bold=True, color=(0, 0.6, 0.6, 1), size_hint_y=None, height=35))
        
        self.su_name = TextInput(hint_text="Full Name", multiline=False, size_hint_y=None, height=42, write_tab=False)
        self.su_email = TextInput(hint_text="Email Address", multiline=False, size_hint_y=None, height=42, write_tab=False, input_type='mail')
        self.su_pass = TextInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=42, write_tab=False)
        self.su_town = TextInput(hint_text="Coastal Area (e.g. Worthing)", multiline=False, size_hint_y=None, height=42, write_tab=False)
        self.su_sport = TextInput(hint_text="Preferred Sport (e.g. Tennis)", multiline=False, size_hint_y=None, height=42, write_tab=False)
        self.su_skill = TextInput(hint_text="Skill Level", multiline=False, size_hint_y=None, height=42, write_tab=False)

        register_btn = OvalButton(text="REGISTER", on_press_callback=self.register_user)
        back_login_btn = OvalButton(text="Back to Login", on_press_callback=lambda x: setattr(self.sm, 'current', 'login'), bg_color=(0.2, 0.2, 0.2, 1))

        signup_layout.add_widget(self.su_name)
        signup_layout.add_widget(self.su_email)
        signup_layout.add_widget(self.su_pass)
        signup_layout.add_widget(self.su_town)
        signup_layout.add_widget(self.su_sport)
        signup_layout.add_widget(self.su_skill)
        signup_layout.add_widget(register_btn)
        signup_layout.add_widget(back_login_btn)

        signup_scroll.add_widget(signup_layout)
        signup_screen.add_widget(signup_scroll)
        self.sm.add_widget(signup_screen)

        # FEED SCREEN
        self.feed_screen = Screen(name="feed")
        main_feed_layout = BoxLayout(orientation="vertical", padding=12, spacing=10)

        header_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=45, spacing=10)
        self.feed_title = Label(text="Open Matches", font_size="20sp", bold=True, color=(0, 0.7, 0.7, 1), size_hint_x=0.5, halign='left')
        self.feed_title.bind(size=self.feed_title.setter('text_size'))

        self.msg_btn = OvalButton(text="Messages", on_press_callback=self.open_inbox, size_hint_x=0.3, bg_color=(0.1, 0.5, 0.5, 1))
        logout_btn = OvalButton(text="Log Out", on_press_callback=self.logout_user, size_hint_x=0.25, bg_color=(0.7, 0.2, 0.2, 1))

        header_box.add_widget(self.feed_title)
        header_box.add_widget(self.msg_btn)
        header_box.add_widget(logout_btn)
        main_feed_layout.add_widget(header_box)

        # Filters
        filter_container = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        filter_container.bind(minimum_height=filter_container.setter("height"))

        self.filter_input = TextInput(hint_text="Search Sport, Town, or Player...", multiline=False, size_hint_y=None, height=40, write_tab=False)
        
        row2_box = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=None, height=40)
        self.date_filter_input = TextInput(hint_text="Date (YYYY-MM-DD)", multiline=False, size_hint_x=0.4, write_tab=False)
        self.venue_filter_input = TextInput(hint_text="Venue", multiline=False, size_hint_x=0.4, write_tab=False)
        filter_apply_btn = OvalButton(text="Search", on_press_callback=self.execute_search, size_hint_x=0.2)

        row2_box.add_widget(self.date_filter_input)
        row2_box.add_widget(self.venue_filter_input)
        row2_box.add_widget(filter_apply_btn)

        filter_container.add_widget(self.filter_input)
        filter_container.add_widget(row2_box)
        main_feed_layout.add_widget(filter_container)

        scroll = ScrollView()
        self.feed_list = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        self.feed_list.bind(minimum_height=self.feed_list.setter("height"))

        scroll.add_widget(self.feed_list)
        main_feed_layout.add_widget(scroll)

        post_btn = OvalButton(text="+ Post New Match", on_press_callback=self.open_post_dialog, bg_color=(0, 0.5, 0.4, 1))
        main_feed_layout.add_widget(post_btn)

        self.feed_screen.add_widget(main_feed_layout)
        self.sm.add_widget(self.feed_screen)

        return self.sm

    # --- LOGIC ---
    def verify_login(self, instance):
        global current_user
        email = self.login_email.text.strip().lower()
        password = self.login_pass.text.strip()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, salt, name, location, sport, skill_level FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and verify_password(password, user[2], user[3]):
            current_user = {"id": user[0], "email": user[1], "name": user[4], "location": user[5], "sport": user[6], "skill_level": user[7]}
            self.sm.current = "feed"
            self.execute_search()
            if not self.poll_event:
                self.poll_event = Clock.schedule_interval(self.load_feed, 3)
            Clock.schedule_once(lambda dt: self.check_match_reminders(), 0.5)
            return

        self.show_dialog("Login Failed", "Invalid email or password.")

    def register_user(self, instance):
        name = self.su_name.text.strip()
        email = self.su_email.text.strip().lower()
        password = self.su_pass.text.strip()
        town = self.su_town.text.strip() or "Worthing"
        sport = self.su_sport.text.strip() or "Tennis"
        skill = self.su_skill.text.strip() or "Intermediate"

        if not name or not email or not password:
            self.show_dialog("Error", "Please fill in Name, Email, and Password.")
            return

        p_hash, salt = hash_password(password)
        user_id = str(uuid.uuid4())

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (id, email, password_hash, salt, name, location, sport, skill_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (user_id, email, p_hash, salt, name, town, sport, skill))
            conn.commit()
            self.show_dialog("Success", "Account created! Please log in.")
            self.sm.current = "login"
        except sqlite3.IntegrityError:
            self.show_dialog("Error", "An account with this email already exists.")
        finally:
            conn.close()

    def logout_user(self, instance):
        global current_user
        if self.poll_event:
            self.poll_event.cancel()
            self.poll_event = None
        current_user = None
        self.cards_dict.clear()
        self.feed_list.clear_widgets()
        self.sm.current = "login"

    def execute_search(self, instance=None):
        self.current_search_query = str(self.filter_input.text or "").strip().lower()
        self.current_date_query = str(self.date_filter_input.text or "").strip().lower()
        self.current_venue_query = str(self.venue_filter_input.text or "").strip().lower()
        self.feed_list.clear_widgets()
        self.cards_dict.clear()
        self.load_feed(force=True)

    def load_feed(self, *args, force=False):
        if not current_user or self.sm.current != "feed":
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT m.id, m.host_id, u.name, m.sport, m.location, m.skill_level, m.match_date, m.match_time, m.venue, m.max_players
        FROM matches m JOIN users u ON m.host_id = u.id ORDER BY m.created_at DESC
        """)
        matches = cursor.fetchall()

        for m in matches:
            m_id, host_id, host_name, sport, loc, skill, date_str, time_str, venue, max_p = m
            cursor.execute("SELECT u.id, u.name FROM match_players mp JOIN users u ON mp.user_id = u.id WHERE mp.match_id = ?", (m_id,))
            players_data = cursor.fetchall()
            player_ids = [p[0] for p in players_data]
            player_names = [p[1] for p in players_data if p[1]]

            if self.current_date_query and self.current_date_query not in str(date_str or "").lower():
                continue
            if self.current_venue_query and self.current_venue_query not in str(venue or "").lower():
                continue
            if self.current_search_query:
                searchable = f"{sport} {loc} {venue} {host_name} " + " ".join(player_names)
                if self.current_search_query not in searchable.lower():
                    continue

            is_host = host_id == current_user["id"]
            is_full = len(player_ids) >= max_p
            badge_text = "HOST" if is_host else ("FULL" if is_full else "OPEN")

            dist = get_coastal_distance(current_user.get("location", ""), loc)
            dist_str = f" • {dist} mi away" if dist is not None and dist > 0 else (" • Local" if dist == 0 else "")

            match_info_text = f"[{badge_text}] {str(sport).upper()} in {loc}{dist_str} ({skill})"
            detail_info_text = f"When: {date_str} at {time_str} ({venue})\nHost: {host_name} | Players ({len(player_ids)}/{max_p}): {', '.join(player_names)}"

            if m_id not in self.cards_dict:
                card = MatchCard()
                match_info = Label(text=match_info_text, font_size="15sp", bold=True, color=(0, 0.8, 0.8, 1), size_hint_y=None, height=25, halign='left')
                match_info.bind(size=match_info.setter('text_size'))

                detail_info = Label(text=detail_info_text, font_size="12sp", color=(0.8, 0.8, 0.8, 1), size_hint_y=None, height=40, halign='left')
                detail_info.bind(size=detail_info.setter('text_size'))

                actions_box = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=40)

                is_attending = current_user["id"] in player_ids
                if is_attending and not is_host:
                    toggle_btn = OvalButton(text="Leave", on_press_callback=lambda x, mid=m_id: self.leave_match(mid), bg_color=(0.8, 0.4, 0.2, 1))
                else:
                    btn_text = "Joined" if is_host else ("Full" if is_full else "Join")
                    toggle_btn = OvalButton(text=btn_text, on_press_callback=lambda x, mid=m_id, req_skill=skill: self.request_join_match(mid, req_skill), bg_color=(0, 0.4, 0.4, 1) if not is_attending and not is_full else (0.3, 0.3, 0.3, 1))

                actions_box.add_widget(toggle_btn)

                if not is_host:
                    msg_host_btn = OvalButton(text="Message", on_press_callback=lambda x, hid=host_id, hname=host_name: self.open_chat_dialog(hid, hname), bg_color=(0.2, 0.5, 0.5, 1))
                    actions_box.add_widget(msg_host_btn)

                if is_host:
                    delete_btn = OvalButton(text="Delete", on_press_callback=lambda x, mid=m_id: self.delete_match(mid), bg_color=(0.8, 0.2, 0.2, 1))
                    actions_box.add_widget(delete_btn)

                card.add_widget(match_info)
                card.add_widget(detail_info)
                card.add_widget(actions_box)

                self.cards_dict[m_id] = {"card": card}
                self.feed_list.add_widget(card)

        conn.close()

    def request_join_match(self, match_id, req_skill):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO match_players (match_id, user_id) VALUES (?, ?)", (match_id, current_user["id"]))
            conn.commit()
            self.show_dialog("Joined!", "You have successfully joined the match.")
            self.execute_search()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def leave_match(self, match_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM match_players WHERE match_id=? AND user_id=?", (match_id, current_user["id"]))
        conn.commit()
        conn.close()
        self.execute_search()

    def delete_match(self, match_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM matches WHERE id=? AND host_id=?", (match_id, current_user["id"]))
        conn.commit()
        conn.close()
        self.execute_search()

    def check_match_reminders(self):
        if not current_user:
            return
        reminders = get_upcoming_reminders(current_user["id"])
        if reminders:
            lines = [f"• {sport} at {venue} ({when})" for sport, venue, when in reminders]
            msg = "Upcoming matches scheduled:\n\n" + "\n".join(lines)
            self.show_dialog("Reminder", msg)

    # --- POST DIALOG ---
    def open_post_dialog(self, instance):
        box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        sport_in = TextInput(hint_text="Sport (e.g. Volleyball)", multiline=False, write_tab=False)
        town_in = TextInput(hint_text="Town (e.g. Worthing)", multiline=False, write_tab=False)
        skill_in = TextInput(hint_text="Skill Level", multiline=False, write_tab=False)
        date_in = TextInput(hint_text="Date (YYYY-MM-DD)", multiline=False, write_tab=False)
        time_in = TextInput(hint_text="Time (e.g. 14:00)", multiline=False, write_tab=False)
        venue_in = TextInput(hint_text="Venue Name", multiline=False, write_tab=False)

        box.add_widget(sport_in)
        box.add_widget(town_in)
        box.add_widget(skill_in)
        box.add_widget(date_in)
        box.add_widget(time_in)
        box.add_widget(venue_in)

        def create_match_action(btn):
            if not sport_in.text.strip() or not town_in.text.strip():
                return
            m_id = str(uuid.uuid4())
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO matches (id, host_id, sport, location, skill_level, match_date, match_time, venue)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (m_id, current_user["id"], sport_in.text.strip(), town_in.text.strip(), skill_in.text.strip(), date_in.text.strip(), time_in.text.strip(), venue_in.text.strip()))
            
            cursor.execute("INSERT INTO match_players (match_id, user_id) VALUES (?, ?)", (m_id, current_user["id"]))
            conn.commit()
            conn.close()
            
            popup.dismiss()
            self.execute_search()

        submit_btn = OvalButton(text="Create Match", on_press_callback=create_match_action)
        box.add_widget(submit_btn)

        popup = Popup(title="Post New Match", content=box, size_hint=(0.9, 0.8))
        popup.open()

    # --- MESSAGING ---
    def open_inbox(self, instance=None):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT u.id, u.name
        FROM users u JOIN direct_messages dm ON (u.id = dm.sender_id OR u.id = dm.receiver_id)
        WHERE (dm.sender_id = ? OR dm.receiver_id = ?) AND u.id != ?
        """, (current_user["id"], current_user["id"], current_user["id"]))
        chats = cursor.fetchall()
        conn.close()

        box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        if not chats:
            box.add_widget(Label(text="No active conversations.", color=(0.8, 0.8, 0.8, 1)))

        for other_id, other_name in chats:
            chat_btn = OvalButton(text=f"Chat with {other_name}", on_press_callback=lambda x, oid=other_id, oname=other_name: self._launch_chat(oid, oname, popup))
            box.add_widget(chat_btn)

        popup = Popup(title="Direct Messages", content=box, size_hint=(0.85, 0.6))
        popup.open()

    def _launch_chat(self, target_id, target_name, parent_popup):
        parent_popup.dismiss()
        self.open_chat_dialog(target_id, target_name)

    def open_chat_dialog(self, target_id, target_name):
        box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        msg_history = Label(text="Loading chat...", size_hint_y=0.7, color=(0.9, 0.9, 0.9, 1), halign='left', valign='bottom')
        msg_history.bind(size=msg_history.setter('text_size'))
        
        input_box = BoxLayout(orientation="horizontal", spacing=5, size_hint_y=0.3)
        msg_input = TextInput(hint_text="Type message...", multiline=False, write_tab=False)
        
        def refresh_chat():
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT sender_id, message FROM direct_messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY timestamp ASC",
                           (current_user["id"], target_id, target_id, current_user["id"]))
            msgs = cursor.fetchall()
            conn.close()
            text = ""
            for sid, msg in msgs:
                sender = "You" if sid == current_user["id"] else target_name
                text += f"{sender}: {msg}\n"
            msg_history.text = text or "No messages yet."

        def send_msg(btn):
            if not msg_input.text.strip():
                return
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO direct_messages (id, sender_id, receiver_id, message) VALUES (?, ?, ?, ?)",
                           (str(uuid.uuid4()), current_user["id"], target_id, msg_input.text.strip()))
            conn.commit()
            conn.close()
            msg_input.text = ""
            refresh_chat()

        send_btn = OvalButton(text="Send", on_press_callback=send_msg, size_hint_x=0.3)
        input_box.add_widget(msg_input)
        input_box.add_widget(send_btn)

        box.add_widget(msg_history)
        box.add_widget(input_box)

        popup = Popup(title=f"Chat with {target_name}", content=box, size_hint=(0.9, 0.7))
        refresh_chat()
        popup.open()

if __name__ == '__main__':
    SportsBeaconApp().run()
