import tkinter as tk
from tkinter import scrolledtext, Entry, Label
from pubsub import pub
from meshtastic.ble_interface import BLEInterface
import threading
import configparser  # Import configparser to read the config file

# Read configuration file to get the node IP address
config = configparser.ConfigParser()
config.read('config.ini')
MAC_ADDRESS = config.get('node', 'MAC_ADDRESS')  # Retrieve the IP address from the config file

def connect_ble():
    """Connect to the Meshtastic device via BLE using a predefined MAC address."""
    print(f"Connecting to BLE device at {MAC_ADDRESS}...")
    try:
        return BLEInterface(MAC_ADDRESS)
    except Exception as e:
        print(f"Failed to connect via BLE: {e}")
        return None


def get_node_info(MAC_ADDRESS):
    print("Initializing BLEInterface to get node info...")
    local = None  # Ensure 'local' is always defined

    try:
        local = BLEInterface(MAC_ADDRESS)
        node_info = local.nodes
        print("Node info retrieved.")
    except Exception as e:
        print(f"Error retrieving node info: {e}")
        node_info = {}
    finally:
        if local:  # Only close if 'local' was successfully initialized
            local.close()

    return node_info


def parse_node_info(node_info):
    print("Parsing node info...")
    nodes = {}
    for node_id, node in node_info.items():
        nodes[node_id] = node.get('user', {}).get('shortName',
                                                  'Unknown')  # Fallback to 'Unknown' if shortName is missing
    print("Node info parsed.")
    return nodes



class MeshtasticGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Meshtastic BLE Chat")

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.config(state=tk.DISABLED)

        self.label = Label(root, text="Press Enter to send")
        self.label.pack(pady=(10, 5))

        # Get and parse node info
        self.node_info = get_node_info(MAC_ADDRESS)
        self.nodes = parse_node_info(self.node_info)

        self.entry = Entry(root, width=40)
        self.entry.pack(pady=10)
        self.entry.bind("<Return>", self.send_message)

        self.local = None
        self.connection_thread = threading.Thread(target=self.init_ble, daemon=True)
        self.connection_thread.start()


    def init_ble(self):
        """Initialize BLE connection in a separate thread."""
        self.local = connect_ble()
        if self.local:
            pub.subscribe(self.on_receive, "meshtastic.receive")
            self.print_message("Connected to Meshtastic via BLE. Listening for messages...")
        else:
            self.print_message("Failed to connect to Meshtastic via BLE.")

    def print_message(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.yview(tk.END)

    def on_receive(self, packet, interface):
        try:
            if packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
                message = packet['decoded']['payload'].decode('utf-8', errors="ignore")
                from_id = packet['fromId']
                node_name = self.nodes.get(from_id, str(from_id))  # Fallback to ID if name_long is not found
                self.print_message(f"{node_name}: {message}")
        except (KeyError, UnicodeDecodeError):
            pass

    def send_message(self, event=None):
        message = self.entry.get()
        if message and self.local:
            threading.Thread(target=self._send_message_thread, args=(message,), daemon=True).start()
            self.entry.delete(0, tk.END)

    def _send_message_thread(self, message):
        try:
            self.local.sendText(text=message)
            self.print_message(f"You: {message}")
        except Exception as e:
            self.print_message(f"Failed to send message: {e}")

    def run(self):
        self.root.mainloop()
        if self.local:
            self.local.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = MeshtasticGUI(root)
    app.run()
