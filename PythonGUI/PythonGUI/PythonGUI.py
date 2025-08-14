import kivy
import gclib
import sys
import datetime
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.button import Button
from kivy.clock import Clock
from functools import partial
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput


class MyGridLayout(GridLayout):



class DMCCodeGUI(App):
    def build(self):
        label = Label(text= "DMC Code Setup App")
        return label


app = DMCCodeGUI()
app.run()



