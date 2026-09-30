import urllib.request
import json
import ssl
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import mainthread
import threading

API_BASE_URL = "https://sports-beacon-api.onrender.com"
ssl_context = ssl._create_unverified_context()

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(
            orientation='vertical',
            padding=[40, 40, 40, 40],
            spacing=15
        )

        # Flexible top spacer
        layout.add_widget(Widget(size_hint_y=1))

        layout.add_widget(Label(
            text="SPORTS BEACON",
            font_size='28sp',
            bold=True,
            color=(0, 0.5, 0.5, 1),
            size_hint_y=None,
            height=45
        ))
        
        layout.add_widget(Label(
            text="Coastal Matchmaking Platform",
            font_size='14sp',
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=25
        ))

        self.email_input = TextInput(
            hint_text="Email",
            multiline=False,
            write_tab=False,
            size_hint_y=None,
            height=48
        )
        layout.add_widget(self.email_input)

        self.password_input = TextInput(
            hint_text="Password",
            password=True,
            multiline=False,
            write_tab=False,
            size_hint_y=None,
            height=48
        )
        layout.add_widget(self.password_input)

        self.login_btn = Button(
            text="LOG IN",
            background_color=(0, 0.4, 0.4, 1),
            size_hint_y=None,
            height=50
        )
        self.login_btn.bind(on_press=self.do_login)
        layout.add_widget(self.login_btn)

        self.register_btn = Button(
            text="REGISTER ACCOUNT",
            background_color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None,
            height=45
        )
        self.register_btn.bind(on_press=self.do_register)
        layout.add_widget(self.register_btn)

        self.status_label = Label(
            text="",
            color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.status_label)

        # Flexible bottom spacer
        layout.add_widget(Widget(size_hint_y=1))
        
        self.add_widget(layout)

    def do_login(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            self.status_label.text = "Please enter email and password."
            return
        self.status_label.text = "Connecting..."
        threading.Thread(target=self._send_request, args=(f"{API_BASE_URL}/login", email, password)).start()

    def do_register(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            self.status_label.text = "Enter email and password to register."
            return
        self.status_label.text = "Registering..."
        threading.Thread(target=self._send_request, args=(f"{API_BASE_URL}/register", email, password)).start()

    def _send_request(self, url, email, password):
        payload = json.dumps({"email": email, "password": password}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=45, context=ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))
                user_email = result.get('user', email)
                self.on_success(f"Welcome {user_email}!", user_email)
        except Exception as e:
            self.update_status("Login failed: Server unreachable", success=False)

    @mainthread
    def update_status(self, message, success=False):
        self.status_label.text = message
        self.status_label.color = (0, 0.7, 0, 1) if success else (0.9, 0.2, 0.2, 1)

    @mainthread
    def on_success(self, message, email):
        # Update dashboard welcome message and switch screen
        dashboard = self.manager.get_screen('dashboard')
        dashboard.welcome_label.text = f"Welcome to Sports Beacon,\n{email}!"
        self.manager.current = 'dashboard'


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(
            orientation='vertical',
            padding=[30, 40, 30, 40],
            spacing=20
        )

        layout.add_widget(Widget(size_hint_y=1))

        self.welcome_label = Label(
            text="Welcome to Sports Beacon!",
            font_size='22sp',
            bold=True,
            halign='center',
            color=(0, 0.6, 0.6, 1),
            size_hint_y=None,
            height=80
        )
        layout.add_widget(self.welcome_label)

        layout.add_widget(Label(
            text="You are successfully authenticated and logged in.",
            font_size='14sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None,
            height=30
        ))

        logout_btn = Button(
            text="LOG OUT",
            background_color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None,
            height=50
        )
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(logout_btn)

        layout.add_widget(Widget(size_hint_y=1))
        
        self.add_widget(layout)

    def logout(self, instance):
        self.manager.current = 'login'


class SportsBeaconApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        return sm


if __name__ == '__main__':
    SportsBeaconApp().run()
