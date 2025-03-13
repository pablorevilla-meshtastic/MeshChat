import tkinter as tk
from tkinter import scrolledtext, Entry, Label
from pubsub import pub
from meshtastic.tcp_interface import TCPInterface

node_ip = '192.168.86.37'  # Replace with your Meshtastic node's IP address


def get_node_info(node_ip):
    print("Initializing TcpInterface to get node info...")
    local = None  # Ensure 'local' is always defined

    try:
        local = TCPInterface(hostname=node_ip)
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
        self.root.title("Meshtastic Chat")

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.config(state=tk.DISABLED)

        # Label above input box with more space
        self.label = Label(root, text="Press Enter to send")
        self.label.pack(pady=(10, 5))  # Added more space above the input box

        self.entry = Entry(root, width=40)
        self.entry.pack(pady=10)  # Increased padding around the input box

        # Bind Enter key to send message
        self.entry.bind("<Return>", self.send_message)

        # Get and parse node info
        self.node_info = get_node_info(node_ip)
        self.nodes = parse_node_info(self.node_info)

        self.local = TCPInterface(hostname=node_ip)
        pub.subscribe(self.on_receive, "meshtastic.receive")
        self.print_message("Listening for messages...")

    def print_message(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.yview(tk.END)

    def on_receive(self, packet, interface):
        try:
            if packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
                message = packet['decoded']['payload'].decode('utf-8')
                from_id = packet['fromId']
                node_name = self.nodes.get(from_id, str(from_id))  # Fallback to ID if name_long is not found
                self.print_message(f"{node_name}: {message}")
        except (KeyError, UnicodeDecodeError):
            pass

    def send_message(self, event=None):
        message = self.entry.get()
        if message:
            self.local.sendText(text=message)
            self.print_message(f"You: {message}")
            self.entry.delete(0, tk.END)

    def run(self):
        self.root.mainloop()
        self.local.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = MeshtasticGUI(root)
    app.run()
