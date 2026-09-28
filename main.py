import os
import sqlite3
import uuid
import hashlib
import json
import urllib.request
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle

DB_NAME = "sports_beacon.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class WhiteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.98, 0.98, 0.98, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

class SportsBeaconApp(App):
    def build(self):
        sm = ScreenManager()
        login_screen = WhiteScreen(name="login")
        
        layout = BoxLayout(orientation="vertical", spacing=14, padding=24, pos_hint={"center_x": 0.5, "center_y": 0.5}, size_hint=(0.9, None))
        layout.bind(minimum_height=layout.setter("height"))

        title = Label(text="SPORTS BEACON", color=(0, 0.4, 0.4, 1), font_size='28sp', bold=True, size_hint_y=None, height=40)
        subtitle = Label(text="Coastal Matchmaking Platform", color=(0.3, 0.3, 0.3, 1), font_size='16sp', size_hint_y=None, height=30)
        
        email_input = TextInput(hint_text="Email Address", multiline=False, size_hint_y=None, height=44)
        pass_input = TextInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=44)
        
        login_btn = Button(text="LOG IN", background_color=(0, 0.4, 0.4, 1), color=(1, 1, 1, 1), size_hint_y=None, height=48)

        layout.add_widget(title)
        layout.add_widget(subtitle)
        layout.add_widget(email_input)
        layout.add_widget(pass_input)
        layout.add_widget(login_btn)

        login_screen.add_widget(layout)
        sm.add_widget(login_screen)
        return sm

if __name__ == "__main__":
    SportsBeaconApp().run()
