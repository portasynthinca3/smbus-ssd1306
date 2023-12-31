import dbus.service

class ScreenService(dbus.service.Object):
    def __init__(self, runner, path, name):
        self.runner = runner
        dbus.service.Object.__init__(self,
                                     dbus.SessionBus(),
                                     path,
                                     dbus.service.BusName(name))

    @dbus.service.method(dbus_interface="ru.psi3.ssd1306.Screen", in_signature="ii")
    def Overtake(self, number, duration):
        self.runner.external_overtake(number, duration / 1000)

    @dbus.service.method(dbus_interface="ru.psi3.ssd1306.Screen")
    def SwitchPin(self):
        self.runner.external_pin_switch()
