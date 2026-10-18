"""Exercise the real Player class without importing optional D-Bus/GLib APIs."""

import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "config/polybar/scripts/player-mpris-tail.py"
)


def load_player_class():
    # Load only the class, avoiding module-level D-Bus setup and CLI execution.
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    player = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Player"
    )
    namespace = {}
    exec(compile(ast.Module(body=[player], type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace["Player"]


class PlayerConnectTests(unittest.TestCase):
    def test_connect_introspects_without_arguments_and_registers_signals(self):
        player_class = load_player_class()
        for has_metadata_signal in (False, True):
            with self.subTest(has_metadata_signal=has_metadata_signal):
                player = player_class.__new__(player_class)
                player._disconnecting = False
                player.bus_name = "org.mpris.MediaPlayer2.example"
                player._signals = {}
                player._session_bus = Mock()
                player._player_interface = Mock()
                player._properties_interface = Mock()
                introspect_calls = []

                def introspect():
                    introspect_calls.append(True)
                    signal = '<signal name="TrackMetadataChanged"/>' if has_metadata_signal else ""
                    return f"<node><interface name='org.mpris.MediaPlayer2.Player'>{signal}</interface></node>"

                # A real zero-argument callable catches accidental D-Bus arguments.
                player._introspect = introspect
                player.connect()

                self.assertEqual(introspect_calls, [True])
                player._player_interface.connect_to_signal.assert_called_once_with(
                    "Seeked", player.onSeeked
                )
                player._properties_interface.connect_to_signal.assert_called_once_with(
                    "PropertiesChanged", player.onPropertiesChanged
                )
                expected_signals = {
                    "seeked": player._player_interface.connect_to_signal.return_value,
                    "properties_changed": player._properties_interface.connect_to_signal.return_value,
                }
                if has_metadata_signal:
                    player._session_bus.add_signal_receiver.assert_called_once_with(
                        player.onMetadataChanged, "TrackMetadataChanged", player.bus_name
                    )
                    expected_signals["track_metadata_changed"] = (
                        player._session_bus.add_signal_receiver.return_value
                    )
                else:
                    player._session_bus.add_signal_receiver.assert_not_called()
                self.assertEqual(player._signals, expected_signals)


if __name__ == "__main__":
    unittest.main()
