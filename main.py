def build(self):
        self.sm = ScreenManager()

        # LOGIN SCREEN (Clean layout without extra clear button)
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
        
        # Robust date parsing (handles both 2027-09-23 and 23/09/2027 inputs)
        raw_date = str(self.date_filter_input.text or "").strip()
        if "/" in raw_date:
            parts = raw_date.split("/")
            if len(parts) == 3:
                # If typed DD/MM/YYYY, reformat to YYYY-MM-DD for database query matching
                raw_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

        self.current_date_query = raw_date.lower()
        self.feed_list.clear_widgets()
        self.cards_dict.clear()
        self.load_feed(force=True)
