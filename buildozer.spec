[app]
title = Sports Beacon
package.name = sportsbeacon
package.domain = org.sportsbeacon
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 0.6.0

# Fixed requirement to allow source compilation without failing prebuilt wheels
requirements = python3,kivy,sqlite3

orientation = portrait
osx.kivy_version = 2.3.0

fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
