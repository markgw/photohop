import pyglet

from pyglet_gui.theme import Theme
from pyglet_gui.manager import Manager
from pyglet_gui.gui import Label


window = pyglet.window.Window(fullscreen=True, vsync=True)
batch = pyglet.graphics.Batch()

@window.event
def on_draw():
    window.clear()
    batch.draw()


theme = Theme({"font": "Lucida Grande",
               "font_size": 12,
               "text_color": [255, 0, 0, 255]}, resources_path='')

label = Label('Hello world')

Manager(label, window=window, theme=theme, batch=batch)

pyglet.app.run()
