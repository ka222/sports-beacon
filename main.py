import urllib.request
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import mainthread
import threading

# YOUR LIVE RENDER URL
API_BASE_URL = "https://sports-beacon-api.onrender.com"

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 30
        self.spacing = 15

        self.add_widget(Label(
            text="SPORTS BEACON",
            font_size=32,
            bold=True,
            color=(0, 0.4, 0.4, 1)
        ))
        
        self.email_input = TextInput(
            hint_text="Email",
            multiline=False,
            write_tab=False
        )
        self.add_widget(self.email_input)

        self.password_input = TextInput(
            hint_text="Password",
            password=True,
            multiline=False,
            write_tab=False
        )
        self.add_widget(self.password_input)

        self.login_btn = Button(
            text="LOG IN",
            background_color=(0, 0.3, 0.3, 1),
            size_hint_y=None,
            height=50
        )
        self.login_btn.bind(on_press=self.do_login)
        self.add_widget(self.login_btn)

        self.status_label = Label(
            text="",
            color=(0.8, 0.2, 0.2, 1)
        )
        self.add_widget(self.status_label)

    def do_login(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()

        if not email or not password:
            self.status_label.text = "Please enter email and password."
            return

        self.status_label.text = "Connecting..."
        # Send request on a background thread to keep UI smooth
        threading.Thread(target=self._send_login_request, args=(email, password)).start()

    def _send_login_request(self, email, password):
        url = f"{API_BASE_URL}/login"
        payload = json.dumps({"email": email, "password": password}).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                self.update_status(f"Success: Welcome {result.get('user', '')}!", success=True)
        except Exception as e:
            self.update_status("Login failed: Network or server error", success=False)

    @mainthread
    def update_status(self, message, success=False):
        self.status_label.text = message
        self.status_label.color = (0, 0.6, 0, 1) if success else (0.8, 0.2, 0.2, 1)


class SportsBeaconApp(App):
    def build(self):
        return LoginScreen()


if __name__ == '__main__':
    SportsBeaconApp().run()
