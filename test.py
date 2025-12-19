from kaki.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.core.window import Window

# Optional fixed size for dev preview
Window.size = (400, 300)

# Build a simple widget class
class RootWidget(BoxLayout):
    pass

# Register it for Kaki
Factory.register('RootWidget', cls=RootWidget)

# Main Hot Reload App
class HotReloadExample(App):
    KV_FILES = ['test.kv']
    CLASSES = {'RootWidget': 'main'}
    AUTORELOADER_PATHS = [( '.', {'recursive': True})]

    def build_app(self):
        return RootWidget()

if __name__ == "__main__":
    HotReloadExample().run()
