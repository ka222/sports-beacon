import urllib.request
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import mainthread
import threading

API_BASE_URL = "https://sports-beacon-api.onrender.com"

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [40, 60, 40, 60]
        self.spacing = 15

        self.add_widget(Label(
            text="SPORTS BEACON",
            font_size='28sp',
            bold=True,
            color=(0, 0.4, 0.4, 1),
            size_hint_y=None,
            height=50
        ))
        
        self.add_widget(Label(
            text="Coastal Matchmaking Platform",
            font_size='14sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=30
        ))

        # Email Input
        self.email_input = TextInput(
            hint_text="Email",
            multiline=False,
            write_tab=False,
            size_hint_y=None,
            height=45
        )
        self.add_widget(self.email_input)

        # Password Input
        self.password_input = TextInput(
            hint_text="Password",
            password=True,
            multiline=False,
            write_tab=False,
            size_hint_y=None,
            height=45
        )
        self.add_widget(self.password_input)

        # Log In Button
        self.login_btn = Button(
            text="LOG IN",
            background_color=(0, 0.3, 0.3, 1),
            size_hint_y=None,
            height=50
        )
        self.login_btn.bind(on_press=self.do_login)
        self.add_widget(self.login_btn)

        # Register Button
        self.register_btn = Button(
            text="REGISTER ACCOUNT",
            background_color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None,
            height=40
        )
        self.register_btn.bind(on_press=self.do_register)
        self.add_widget(self.register_btn)

        # Status Label
        self.status_label = Label(
            text="",
            color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.status_label)

    def do_login(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()

        if not email or not password:
            self.status_label.text = "Please enter email and password."
            return

        self.status_label.text = "Connecting to backend..."
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
            headers={'Content-Type': 'application/json'}
        )

        try:
            # Increased timeout to 45 seconds to handle Render free-tier cold starts
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode('utf-8'))
                self.update_status(f"Success: {result.get('message', 'Done!')}", success=True)
        except Exception:
            self.update_status("Login failed: Server sleeping or unreachable", success=False)

    @mainthread
    def update_status(self, message, success=False):
        self.status_label.text = message
        self.status_label.color = (0, 0.6, 0, 1) if success else (0.8, 0.2, 0.2, 1)


class SportsBeaconApp(App):
    def build(self):
        return LoginScreen()


if __name__ == '__main__':
    SportsBeaconApp().run()
