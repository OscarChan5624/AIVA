from kivy.app import App as KivyApp
from kivy.core.window import Window
from kivy.factory import Factory
from kaki.app import App as KakiApp

class Home(KakiApp, KivyApp):
    KV_FILES = ['design.kv']            # auto-reload KV on save
    CLASSES = {}                        # no Python classes to reload
    AUTORELOADER_PATHS = [('.', {'recursive': True})]

    def build(self):
        Window.size = (360, 640)
        Window.minimum_width = 360
        Window.minimum_height = 640
        Window.maximum_width = 430
        Window.maximum_height = 900
        return Factory.BoxExample()     # defined in design.kv

if __name__ == '__main__':
    Home().run()