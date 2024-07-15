"""Module to test the main napp file."""

from unittest.mock import Mock, MagicMock

from kytos.core import Controller
from kytos.core.config import KytosConfig
from napps.kytos.flow_manager.main import Main


class TestMain:
    """Test the Main class."""

    def setup_method(self):
        """Execute steps before each tests."""
        Main.get_flow_controller = MagicMock()
        self.napp = Main(self.get_controller_mock())

    @staticmethod
    def get_controller_mock():
        """Return a controller mock."""
        options = KytosConfig().options["daemon"]
        controller = Controller(options)
        controller.log = Mock()
        return controller

    def test_add_flow_mod_sent_ok(self):
        self.napp._flow_mods_sent_max_size = 3
        flow = Mock()
        xid = "12345"
        command = "add"
        initial_len = len(self.napp._flow_mods_sent)
        self.napp._add_flow_mod_sent(xid, flow, command, "no_owner")

        assert len(self.napp._flow_mods_sent) == initial_len + 1
        assert self.napp._flow_mods_sent.get(xid, None) == (flow, command, "no_owner")

    def test_add_flow_mod_sent_overlimit(self):
        self.napp._flow_mods_sent_max_size = 5
        xid = "23456"
        command = "add"
        while len(self.napp._flow_mods_sent) < 5:
            xid += "1"
            flow = Mock()
            self.napp._add_flow_mod_sent(xid, flow, command, "no_owner")

        xid = "90876"
        flow = Mock()
        initial_len = len(self.napp._flow_mods_sent)
        self.napp._add_flow_mod_sent(xid, flow, command, "no_owner")

        assert len(self.napp._flow_mods_sent) == initial_len
        assert self.napp._flow_mods_sent.get(xid, None) == (flow, command, "no_owner")
