from collections import defaultdict, Counter
import re
import tkinter as tk
from tkinter import ttk

log_file_path = 'c:\\Users\\jacob\\Desktop\\murp\\log.txt'
output_file_path = 'c:\\Users\\jacob\\Desktop\\murp\\log_stats.txt'

def parse_log_file(log_file_path):
    user_stats = defaultdict(lambda: {'messages_sent': 0, 'words': Counter()})
    
    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                match = re.match(r'Message from \[ (.+?) \]: "(.+?)" \[', line)
                if match:
                    user, message = match.groups()
                    user_stats[user]['messages_sent'] += 1
                    words = message.split()
                    user_stats[user]['words'].update(words)
    except FileNotFoundError:
        print(f"Error: The file at {log_file_path} was not found.")
    
    return user_stats

def generate_statistics(user_stats):
    stats = {}
    for user, data in user_stats.items():
        most_common_word, _ = data['words'].most_common(1)[0] if data['words'] else ('None', 0)
        stats[user] = {
            'messages_sent': data['messages_sent'],
            'favorite_word': most_common_word,
        }
    return stats

def display_statistics(stats):
    with open(output_file_path, 'w') as output_file:
        for user, data in stats.items():
            output_file.write(f"User: {user}\n")
            output_file.write(f"Messages Sent: {data['messages_sent']}\n")
            output_file.write(f"Favorite Word: {data['favorite_word']}\n")
            output_file.write("\n")

if __name__ == "__main__":
    user_stats = parse_log_file(log_file_path)
    stats = generate_statistics(user_stats)
    display_statistics(stats)
