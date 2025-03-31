import tkinter as tk
from tkinter import scrolledtext, Entry, Label, Listbox
from pubsub import pub
from meshtastic.tcp_interface import TCPInterface
import configparser  # To read the config file

# Read configuration file to get the node IP address
config = configparser.ConfigParser()
config.read('config.ini')
node_ip = config.get('node', 'node_ip')  # Retrieve the IP address from the config file

def get_node_info(node_ip):
    print("Initializing TCPInterface to get node info...")
    try:
        local = TCPInterface(hostname=node_ip)
        node_info = local.nodes
        print("Node info retrieved.")
        return node_info, local
    except Exception as e:
        print(f"Error retrieving node info: {e}")
        return {}, None  # Return empty data if there's an issue


def parse_node_info(node_info):
    print("Parsing node info...")
    nodes = {}
    node_list = []

    for index, (node_id, node) in enumerate(node_info.items()):
        short_name = node.get('user', {}).get('shortName', 'Unknown')
        long_name = node.get('user', {}).get('longName', 'Unknown')
        nodes[node_id] = short_name
        node_list.append(f"{short_name} - {long_name}")

    print("Node info parsed.")
    return nodes, node_list


class MeshtasticGUI:
    def __init__(self, root):
        self.node_info, self.local = get_node_info(node_ip)
        self.nodes, self.node_list = parse_node_info(self.node_info)

        local_node_name = "Meshtastic Chat"  # Default title if no nodes are found
        if self.node_list:
            local_node_name = self.node_list.pop(0)  # Use the first node name as title and remove it from the list

        self.root = root
        self.root.title(local_node_name)

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.config(state=tk.DISABLED)

        self.label = Label(root, text="Press Enter to send")
        self.label.pack(pady=(10, 5))

        self.entry = Entry(root, width=40)
        self.entry.pack(pady=10)
        self.entry.bind("<Return>", self.send_message)

        self.listbox = Listbox(root, height=6)
        self.listbox.pack(padx=10, pady=10, fill=tk.BOTH)
        for node_entry in self.node_list:
            self.listbox.insert(tk.END, node_entry)

        if self.local:
            print("Connected nodes:", self.local.nodes)  # Debugging
            pub.subscribe(self.on_receive, "meshtastic.receive")
            self.print_message("Connected to Meshtastic. Listening for messages...")
        else:
            self.print_message("Failed to connect to Meshtastic node.")

    def print_message(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.yview(tk.END)

    def on_receive(self, packet, interface):
        print(f"Received packet: {packet}")  # Debugging
        try:
            if packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
                message = packet['decoded']['payload'].decode('utf-8')
                from_id = packet['fromId']
                node_name = self.nodes.get(from_id, str(from_id))
                self.print_message(f"{node_name}: {message}")
        except (KeyError, UnicodeDecodeError, AttributeError) as e:
            print(f"Error decoding message: {e}")  # Debugging

    def send_message(self, event=None):
        message = self.entry.get()
        if message and self.local:
            self.local.sendText(text=message)
            self.print_message(f"You: {message}")
            self.entry.delete(0, tk.END)

    def run(self):
        self.root.mainloop()
        if self.local:
            self.local.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = MeshtasticGUI(root)
    app.run()
