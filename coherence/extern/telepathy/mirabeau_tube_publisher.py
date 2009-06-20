
import telepathy

from coherence.extern.telepathy import tube, client, mirabeau_tube_consumer
from coherence.dbus_constants import BUS_NAME, OBJECT_PATH

class MirabeauTubePublisherMixin(tube.TubePublisherMixin):
    def __init__(self, tubes_to_offer, application, allowed_devices):
        super(MirabeauTubePublisherMixin, self).__init__(tubes_to_offer)
        self.coherence = application
        self.allowed_devices = allowed_devices

    def tube_opened(self, id):
        super(MirabeauTubePublisherMixin, self).tube_opened(id)
        self.coherence.dbus.add_to_connection(self.tube_conn, OBJECT_PATH)
        for device in self.coherence.dbus.devices.values():
            self._register_device(device)
        self.coherence.dbus.bus.add_signal_receiver(self._media_server_found,
                                                    "UPnP_ControlPoint_MediaServer_detected")
        self.coherence.dbus.bus.add_signal_receiver(self._media_server_removed,
                                                    "UPnP_ControlPoint_MediaServer_removed")

    def _media_server_found(self, infos, udn):
        uuid = udn[5:]
        for device in self.coherence.dbus.devices.values():
            if device.uuid == uuid:
                self._register_device(device)
                return

    def _register_device(self, device):
        name = '%s (%s)' % (device.get_friendly_name(),
                            ':'.join(device.get_device_type().split(':')[3:5]))
        self.info("device found: %s" % name)
        if self.allowed_devices != None and device.uuid not in self.allowed_devices:
            self.debug("device not allowed: %r", device.uuid)
            return
        try:
            device.add_to_connection(self.tube_conn, device.path())
            self.debug("device add_to_connection: %s" % name)
        except Exception, exc:
            # XXX: remove this when Pontoon doesn't store duplicates anymore
            pass
        else:
            for service in device.services:
                service.add_to_connection(self.tube_conn, service.path)

    def _media_server_removed(self, udn):
        for device in self.coherence.dbus.devices.values():
            if udn == device.device.get_id():
                if self.allowed_devices != None and device.uuid not in self.allowed_devices:
                    # the device is not allowed, no reason to
                    # disconnect from the tube to which it wasn't
                    # connected in the first place anyway
                    return
                try:
                    device.remove_from_connection(self.tube_conn, device.path())
                    self.debug("remove_from_connection: %s" % device.get_friendly_name())
                except:
                    # XXX: remove this when Pontoon doesn't store duplicates anymore
                    continue
                else:
                    for service in device.services:
                        service.remove_from_connection(self.tube_conn, service.path)
                    return

class MirabeauTubePublisher(MirabeauTubePublisherMixin, client.Client):

    def __init__(self, connection, muc_id, tubes_to_offer, application,
                 allowed_devices):
        MirabeauTubePublisherMixin.__init__(self, tubes_to_offer, application,
                                            allowed_devices)
        client.Client.__init__(self, connection, muc_id)

class MirabeauTubePublisherConsumer(MirabeauTubePublisherMixin,
                                    mirabeau_tube_consumer.MirabeauTubeConsumerMixin,
                                    client.Client):
    def __init__(self, connection, muc_id, tubes_to_offer, application,
                 allowed_devices, found_peer_callback=None,
                 disapeared_peer_callback=None, got_devices_callback=None):
        MirabeauTubePublisherMixin.__init__(self, tubes_to_offer, application,
                                            allowed_devices)
        kwargs = dict(found_peer_callback=found_peer_callback,
                      disapeared_peer_callback=disapeared_peer_callback,
                      got_devices_callback=got_devices_callback)
        mirabeau_tube_consumer.MirabeauTubeConsumerMixin.__init__(self, **kwargs)
        client.Client.__init__(self, connection, muc_id)
