#!/usr/bin/env python3

import tkinter as tk
from tkinter import scrolledtext, Entry, Label
from pubsub import pub
from meshtastic.tcp_interface import TCPInterface
import configparser
import sys
from datetime import datetime  # 🕒 Added for timestamps

# Redirect print statements to a Tkinter Text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        pass  # Needed for compatibility

# Read configuration file
config = configparser.ConfigParser()
config.read('config.ini')

try:
    node_ip = config.get('node', 'node_ip')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print(f"Configuration error: {e}")
    sys.exit("Missing or invalid 'node_ip' in config.ini. Exiting...")

def get_node_info(node_ip):
    print("Initializing TCPInterface to get node info...")
    try:
        local = TCPInterface(hostname=node_ip)
        node_info = local.nodes
        print("Node info retrieved.")
        return node_info, local
    except Exception as e:
        print(f"Error retrieving node info: {e}")
        return {}, None

def parse_node_info(node_info):
    print("Parsing node info...")
    nodes = {}
    node_list = []
    for node_id, node in node_info.items():
        short_name = node.get('user', {}).get('shortName', 'Unknown')
        long_name = node.get('user', {}).get('longName', 'Unknown')
        nodes[node_id] = short_name
        node_list.append(f"{short_name} - {long_name}")
    print("Node info parsed.")
    return nodes, node_list

class MeshtasticGUI:
    def __init__(self, root):
        self.root = root
        self.receive_count = 0
        self.node_info, self.local = get_node_info(node_ip)
        self.nodes, self.node_list = parse_node_info(self.node_info)

        # Try to get local node's short and long name
        local_node_name = "Meshtastic Chat"
        if self.node_list:
            local_node_name = self.node_list.pop(0)

        self.root.title(local_node_name)

        # Panel 1: Chat log
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=15)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.config(state=tk.DISABLED)

        # Panel 2: Debug console
        self.console_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=10, bg="#111", fg="#0f0")
        self.console_area.pack(padx=10, pady=(0, 10))
        self.console_area.config(state=tk.DISABLED)

        # Redirect stdout and stderr
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = RedirectText(self.console_area)
        sys.stderr = RedirectText(self.console_area)

        print("Discovered nodes:")
        print("--------------------------")
        for node in self.node_list:
            print(f"{node}")
        print("--------------------------")
        print("Packets:")

        # Panel 3: Entry and node count
        self.label = Label(root, text=f"Nodes online: {len(self.nodes)}")
        self.label.pack(pady=(0, 5))
        self.label = Label(root, text=f"Press Enter to send")
        self.label.pack(pady=(0, 5))
        self.entry = Entry(root, width=40)
        self.entry.pack(pady=(0, 10))
        self.entry.bind("<Return>", self.send_message)

        if self.local:
            pub.subscribe(self.on_receive, "meshtastic.receive")
            self.print_message("Listening for text messages...")
        else:
            self.print_message("Failed to connect to Meshtastic node.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def print_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.yview(tk.END)

    def on_receive(self, packet, interface):
        def update_gui():
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.receive_count += 1
                decoded = packet.get('decoded', {})
                from_id = packet.get('fromId', 'unknown')
                node_name = self.nodes.get(from_id, str(from_id))
                portnum = decoded.get('portnum', 'unknown')
                if node_name != "None" and from_id != "None":
                    print(f"[{timestamp}] - {node_name} ({from_id}), {portnum}")

                if portnum == 'TEXT_MESSAGE_APP':
                    payload = decoded.get('payload')
                    if isinstance(payload, bytes):
                        message = payload.decode('utf-8')
                        self.print_message(f"{node_name}: {message}")
            except Exception as e:
                print(f"Error decoding message: {e}")

        self.root.after(0, update_gui)

    def send_message(self, event=None):
        message = self.entry.get()
        if message and self.local:
            self.local.sendText(text=message)
            self.print_message(f"You: {message}")
            self.entry.delete(0, tk.END)

    def on_close(self):
        print("Closing app...")
        if self.local:
            self.local.close()
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = MeshtasticGUI(root)
    app.run()
