import os
import sqlite3
import hashlib
import hmac
import uuid
from datetime import datetime

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle

DB_NAME = "sports_beacon.db"

# ==========================================
# DATABASE HELPER FUNCTIONS
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL,
            name TEXT NOT NULL,
            town TEXT NOT NULL,
            preferred_sport TEXT NOT NULL,
            skill_level TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            sport TEXT NOT NULL,
            town TEXT NOT NULL,
            skill_level TEXT NOT NULL,
            match_date TEXT NOT NULL,
            match_time TEXT NOT NULL,
            venue TEXT NOT NULL,
            max_players INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY (host_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_players (
            match_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            PRIMARY KEY (match_id, user_id),
            FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            match_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key, salt

def verify_password(stored_password_hash, stored_salt, provided_password):
    key, _ = hash_password(provided_password, stored_salt)
    return hmac.compare_digest(key, stored_password_hash)


# ==========================================
# CUSTOM UI COMPONENTS
# ==========================================

class OvalButton(Button):
    def __init__(self, bg_color=(0, 0.6, 0.6, 1), text_color=(1, 1, 1, 1), on_press_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.color = text_color
        self.bold = True
        self.bg_color = bg_color
        self.on_press_callback = on_press_callback

        with self.canvas.before:
            self.rect_color = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press(self):
        if self.on_press_callback:
            self.on_press_callback(self)


# ==========================================
# MAIN APPLICATION CLASS
# ==========================================

class SportsBeaconApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = None
        self.cards_dict = {}
        self.poll_event = None
        self.msg_poll_event = None
        self.active_chat_match_id = None

        self.current_search_query = ""
        self.current_date_query = ""
        self.current_venue_query = ""

    def build(self):
        init_db()
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

        login_btn = OvalButton(text="LOG IN", on_press_callback=self.verify_login)
        signup_redirect_btn = OvalButton(text="Create an Account", on_press_callback=lambda x: setattr(self.sm, 'current', 'signup'), bg_color=(0.2, 0.2, 0.2, 1))

        layout.add_widget(self.login_email)
        layout.add_widget(self.login_pass)
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

    def execute_search(self, instance=None):
        self.current_search_query = str(self.filter_input.text or "").strip().lower()
        self.current_venue_query = str(self.venue_filter_input.text or "").strip().lower()
        
        raw_date = str(self.date_filter_input.text or "").strip()
        if "/" in raw_date:
            parts = raw_date.split("/")
            if len(parts) == 3:
                raw_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

        self.current_date_query = raw_date.lower()
        self.feed_list.clear_widgets()
        self.cards_dict.clear()
        self.load_feed(force=True)

    def register_user(self, instance):
        email = self.su_email.text.strip().lower()
        password = self.su_pass.text.strip()
        name = self.su_name.text.strip()
        town = self.su_town.text.strip()
        sport = self.su_sport.text.strip()
        skill = self.su_skill.text.strip()

        if not all([email, password, name, town, sport, skill]):
            self.show_popup("Error", "All fields are required.")
            return

        key, salt = hash_password(password)
        user_id = str(uuid.uuid4())

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, salt, name, town, preferred_sport, skill_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, key, salt, name, town, sport, skill))
            conn.commit()
            conn.close()

            self.show_popup("Success", "Account created successfully! Please log in.")
            self.sm.current = 'login'
        except sqlite3.IntegrityError:
            self.show_popup("Error", "An account with that email already exists.")

    def verify_login(self, instance):
        email = self.login_email.text.strip().lower()
        password = self.login_pass.text.strip()

        if not email or not password:
            self.show_popup("Error", "Please enter your email and password.")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and verify_password(user["password_hash"], user["salt"], password):
            self.current_user = dict(user)
            self.sm.current = 'feed'
            self.load_feed(force=True)
            if not self.poll_event:
                self.poll_event = Clock.schedule_interval(self.load_feed, 3)
        else:
            self.show_popup("Error", "Invalid email or password.")

    def logout_user(self, instance):
        if self.poll_event:
            self.poll_event.cancel()
            self.poll_event = None
        if self.msg_poll_event:
            self.msg_poll_event.cancel()
            self.msg_poll_event = None
        
        self.current_user = None
        self.cards_dict.clear()
        self.feed_list.clear_widgets()
        self.sm.current = 'login'

    def load_feed(self, dt=None, force=False):
        if not self.current_user or self.sm.current != 'feed':
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, u.name as host_name 
            FROM matches m
            JOIN users u ON m.host_id = u.id
            ORDER BY m.match_date ASC, m.match_time ASC
        """)
        matches = cursor.fetchall()

        for m in matches:
            m_id = m["id"]
            
            cursor.execute("""
                SELECT u.id, u.name 
                FROM match_players mp
                JOIN users u ON mp.user_id = u.id
                WHERE mp.match_id = ?
            """, (m_id,))
            players = cursor.fetchall()
            player_ids = [p["id"] for p in players]

            search_str = f"{m['sport']} {m['town']} {m['host_name']}".lower()
            if self.current_search_query and self.current_search_query not in search_str:
                continue
            if self.current_date_query and self.current_date_query not in m['match_date'].lower():
                continue
            if self.current_venue_query and self.current_venue_query not in m['venue'].lower():
                continue

            if m_id not in self.cards_dict or force:
                card = self.create_match_card(m, player_ids)
                self.cards_dict[m_id] = card
                self.feed_list.add_widget(card)

        conn.close()

    def create_match_card(self, m, player_ids):
        card = BoxLayout(orientation="vertical", spacing=6, padding=10, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))

        with card.canvas.before:
            Color(0.12, 0.12, 0.15, 1)
            rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[8])
        card.bind(pos=lambda obj, val: setattr(rect, 'pos', val), size=lambda obj, val: setattr(rect, 'size', val))

        title = f"[HOST] {m['sport'].upper()} in {m['town']} • {m['skill_level']}"
        card.add_widget(Label(text=title, markup=True, bold=True, color=(0, 0.8, 0.8, 1), size_hint_y=None, height=25, halign='left'))

        details = f"Date: {m['match_date']} @ {m['match_time']}\nVenue: {m['venue']}\nPlayers: {len(player_ids)}/{m['max_players']}"
        card.add_widget(Label(text=details, size_hint_y=None, height=50, halign='left', color=(0.9, 0.9, 0.9, 1)))

        btn_box = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=36)
        
        is_host = (m['host_id'] == self.current_user["id"])
        is_joined = (self.current_user["id"] in player_ids)

        if is_host:
            del_btn = OvalButton(text="Delete", on_press_callback=lambda x: self.delete_match(m['id']), bg_color=(0.8, 0.2, 0.2, 1))
            btn_box.add_widget(del_btn)
        elif is_joined:
            leave_btn = OvalButton(text="Leave Match", on_press_callback=lambda x: self.leave_match(m['id']), bg_color=(0.6, 0.4, 0.2, 1))
            btn_box.add_widget(leave_btn)
        else:
            join_btn = OvalButton(text="Join", on_press_callback=lambda x: self.join_match(m['id'], len(player_ids), m['max_players']))
            btn_box.add_widget(join_btn)

        chat_btn = OvalButton(text="Chat", on_press_callback=lambda x: self.open_chat_dialog(m['id']), bg_color=(0.2, 0.4, 0.6, 1))
        btn_box.add_widget(chat_btn)

        card.add_widget(btn_box)
        return card

    def join_match(self, match_id, current_p, max_p):
        if current_p >= max_p:
            self.show_popup("Error", "Match is already full!")
            return

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO match_players (match_id, user_id) VALUES (?, ?)", (match_id, self.current_user["id"]))
            conn.commit()
            self.show_popup("Success", "Joined match!")
        except sqlite3.IntegrityError:
            self.show_popup("Notice", "You are already in this match.")
        conn.close()
        self.execute_search()

    def leave_match(self, match_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM match_players WHERE match_id=? AND user_id=?", (match_id, self.current_user["id"]))
        conn.commit()
        conn.close()
        self.show_popup("Success", "Left match.")
        self.execute_search()

    def delete_match(self, match_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM matches WHERE id=? AND host_id=?", (match_id, self.current_user["id"]))
        conn.commit()
        conn.close()
        self.show_popup("Success", "Match deleted.")
        self.execute_search()

    def open_post_dialog(self, instance):
        content = BoxLayout(orientation="vertical", spacing=8, padding=10)
        
        sport_in = TextInput(hint_text="Sport (e.g. Football)", multiline=False, write_tab=False)
        town_in = TextInput(hint_text="Town/City", multiline=False, write_tab=False)
        skill_in = TextInput(hint_text="Skill Level (e.g. Intermediate)", multiline=False, write_tab=False)
        date_in = TextInput(hint_text="Date (YYYY-MM-DD)", multiline=False, write_tab=False)
        time_in = TextInput(hint_text="Time (HH:MM)", multiline=False, write_tab=False)
        venue_in = TextInput(hint_text="Venue Name", multiline=False, write_tab=False)
        max_p_in = TextInput(hint_text="Max Players (e.g. 10)", multiline=False, input_filter='int', write_tab=False)

        content.add_widget(sport_in)
        content.add_widget(town_in)
        content.add_widget(skill_in)
        content.add_widget(date_in)
        content.add_widget(time_in)
        content.add_widget(venue_in)
        content.add_widget(max_p_in)

        popup = Popup(title="Post New Match", content=content, size_hint=(0.9, 0.85))

        def submit(btn_instance):
            s = sport_in.text.strip()
            t = town_in.text.strip()
            sk = skill_in.text.strip()
            d = date_in.text.strip()
            tm = time_in.text.strip()
            v = venue_in.text.strip()
            mp = max_p_in.text.strip()

            if not all([s, t, sk, d, tm, v, mp]):
                self.show_popup("Error", "Please fill in all fields.")
                return

            if "/" in d:
                parts = d.split("/")
                if len(parts) == 3:
                    d = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

            m_id = str(uuid.uuid4())
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO matches (id, host_id, sport, town, skill_level, match_date, match_time, venue, max_players)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (m_id, self.current_user["id"], s, t, sk, d, tm, v, int(mp)))
            
            cursor.execute("INSERT INTO match_players (match_id, user_id) VALUES (?, ?)", (m_id, self.current_user["id"]))
            conn.commit()
            conn.close()

            popup.dismiss()
            self.show_popup("Success", "Match posted!")
            self.execute_search()

        post_sub_btn = OvalButton(text="Publish Match", on_press_callback=submit)
        content.add_widget(post_sub_btn)
        popup.open()

    def open_chat_dialog(self, match_id):
        self.active_chat_match_id = match_id
        content = BoxLayout(orientation="vertical", spacing=8, padding=10)

        scroll = ScrollView()
        msg_list = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        msg_list.bind(minimum_height=msg_list.setter("height"))
        scroll.add_widget(msg_list)
        content.add_widget(scroll)

        input_box = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=None, height=40)
        msg_input = TextInput(hint_text="Type a message...", multiline=False, write_tab=False)
        send_btn = OvalButton(text="Send", size_hint_x=0.25)
        
        input_box.add_widget(msg_input)
        input_box.add_widget(send_btn)
        content.add_widget(input_box)

        popup = Popup(title="Match Chat", content=content, size_hint=(0.9, 0.8))

        def load_messages(dt=None):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE match_id=? ORDER BY timestamp ASC", (self.active_chat_match_id,))
            msgs = cursor.fetchall()
            conn.close()

            msg_list.clear_widgets()
            for msg in msgs:
                txt = f"[b]{msg['sender_name']}[/b]: {msg['message']}"
                lbl = Label(text=txt, markup=True, size_hint_y=None, height=28, halign='left', color=(0.9, 0.9, 0.9, 1))
                msg_list.add_widget(lbl)

        def send_msg(btn):
            txt = msg_input.text.strip()
            if not txt:
                return
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (id, match_id, sender_id, sender_name, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), self.active_chat_match_id, self.current_user["id"], self.current_user["name"], txt, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()

            msg_input.text = ""
            load_messages()

        send_btn.on_press_callback = send_msg
        load_messages()

        self.msg_poll_event = Clock.schedule_interval(load_messages, 2)

        def on_dismiss(instance):
            if self.msg_poll_event:
                self.msg_poll_event.cancel()
                self.msg_poll_event = None
            self.active_chat_match_id = None

        popup.bind(on_dismiss=on_dismiss)
        popup.open()

    def open_inbox(self, instance):
        self.show_popup("Inbox", "Select 'Chat' directly on any match card to view or send group messages.")

    def show_popup(self, title, message):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        content.add_widget(Label(text=message, color=(1, 1, 1, 1)))
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        close_btn = OvalButton(text="OK", on_press_callback=lambda x: popup.dismiss())
        content.add_widget(close_btn)
        popup.open()


if __name__ == "__main__":
    SportsBeaconApp().run()
