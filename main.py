import re
from collections import defaultdict
import os
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time

class HandHistory:
    def __init__(self, hand_id, seat, hole_cards, actions, player_count):
        self.hand_id = hand_id
        self.seat = seat
        self.hole_cards = hole_cards
        self.actions = actions
        self.player_count = player_count

def parse_winamax_hand_history(file_content, username):
    hands = []
    hand_blocks = re.split(r'Winamax Poker - Tournament ".*?" buyIn:', file_content)[1:]
    
    print(f"Total hand blocks found: {len(hand_blocks)}")
    
    for i, block in enumerate(hand_blocks):
        print(f"Processing block {i+1}/{len(hand_blocks)}")
        
        # Explicitly check for non-Expresso tournaments
        if "Expresso" not in block and "Hold'em" in block:
            hand_id_match = re.search(r'HandId: #(\d+-\d+-\d+)', block)
            seat_match = re.search(fr'Seat \d+: {username} \(\d+\)', block)
            hole_cards_match = re.search(fr'{username} shows \[(.+?)\]', block)
            actions = re.findall(r'(.*?): (folds|raises|calls|checks|bets)', block)
            player_count = len(re.findall(r'Seat \d+:', block))
            
            if hand_id_match and seat_match and hole_cards_match and player_count == 6:
                seat = int(re.search(fr'Seat (\d+): {username}', block).group(1))
                hole_cards = hole_cards_match.group(1).split()
                hand = HandHistory(
                    hand_id=hand_id_match.group(1),
                    seat=seat,
                    hole_cards=hole_cards,
                    actions=actions,
                    player_count=player_count
                )
                hands.append(hand)
                print(f"  Valid hand found: {hand.hand_id}, Seat: {hand.seat}, Hole cards: {hand.hole_cards}")
            else:
                print("  Invalid hand (missing data or not 6-max)")
        else:
            print("  Skipping Expresso or non-Hold'em tournament")
    
    print(f"Total valid hands found: {len(hands)}")
    return hands

def position_mapping_6max(seat):
    position_map = {
        1: "UTG", 2: "HJ", 3: "CO", 4: "BTN", 5: "SB", 6: "BB"
    }
    return position_map.get(seat, "Unknown")

def get_hand_type(hole_cards):
    ranks = '23456789TJQKA'
    card1, card2 = hole_cards
    rank1, suit1 = card1[0], card1[1]
    rank2, suit2 = card2[0], card2[1]
    
    if rank1 == rank2:
        return f"{rank1}{rank2}"
    elif suit1 == suit2:
        return f"{max(rank1, rank2)}{min(rank1, rank2)}s"
    else:
        return f"{max(rank1, rank2)}{min(rank1, rank2)}o"

def analyze_hands(hands, username):
    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for hand in hands:
        position = position_mapping_6max(hand.seat)
        hand_type = get_hand_type(hand.hole_cards)
        stats[position]['total_hands'][hand_type] += 1
        
        open_raise = False
        first_action = True
        for player, action in hand.actions:
            if player == username:
                if action == 'raises' and first_action:
                    open_raise = True
                break
            elif action in ['raises', 'bets']:
                first_action = False
        
        if open_raise:
            stats[position]['open_raises'][hand_type] += 1
        
        print(f"Processed hand: {hand.hand_id}, Position: {position}, Hand type: {hand_type}, Open raise: {open_raise}")

    return stats

def generate_report(folder_path, username):
    all_hands = []
    start_time = time.time()
    total_files = sum(1 for f in os.listdir(folder_path) if f.endswith('.txt') and 'summary' not in f.lower())
    processed_files = 0

    print(f"Found {total_files} files to process.")

    for filename in os.listdir(folder_path):
        if filename.endswith('.txt') and 'summary' not in filename.lower():
            file_start_time = time.time()
            print(f"Processing tournament: {filename}")
            try:
                with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as file:
                    content = file.read()
                    hands = parse_winamax_hand_history(content, username)
                    if hands:
                        all_hands.extend(hands)
                        print(f"  Found {len(hands)} valid hands in this file.")
                    else:
                        print(f"  No valid hands found in {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
            
            processed_files += 1
            file_end_time = time.time()
            print(f"  Processed file {processed_files} of {total_files} in {file_end_time - file_start_time:.2f} seconds")
            print(f"  Total hands processed so far: {len(all_hands)}")
            print(f"  Overall progress: {processed_files/total_files*100:.2f}%")
            print()

    if not all_hands:
        print("No hands were parsed from any files. Please check your input data and username.")
        return None

    end_time = time.time()
    print(f"Finished processing all files in {end_time - start_time:.2f} seconds")
    print(f"Total hands processed: {len(all_hands)}")
    
    print("Analyzing hands...")
    analysis_start_time = time.time()
    stats = analyze_hands(all_hands, username)
    analysis_end_time = time.time()
    print(f"Hand analysis completed in {analysis_end_time - analysis_start_time:.2f} seconds")

    return stats

def generate_heatmap(stats):
    if not stats:
        print("No data available to generate heatmap.")
        return

    positions = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    ranks = '23456789TJQKA'
    
    for position in positions:
        if position not in stats:
            continue
        
        print(f"Generating heatmap for position: {position}")
        heatmap_start_time = time.time()
        
        matrix = np.zeros((13, 13))
        for i, rank1 in enumerate(ranks):
            for j, rank2 in enumerate(ranks):
                if i > j:
                    hand_type = f"{rank1}{rank2}o"
                elif i < j:
                    hand_type = f"{rank2}{rank1}s"
                else:
                    hand_type = f"{rank1}{rank2}"
                
                total_hands = stats[position]['total_hands'][hand_type]
                open_raises = stats[position]['open_raises'][hand_type]
                percentage = (open_raises / total_hands * 100) if total_hands > 0 else 0
                matrix[i, j] = percentage
                
                print(f"Position: {position}, Hand: {hand_type}, Total: {total_hands}, Open Raises: {open_raises}, Percentage: {percentage:.2f}%")

        plt.figure(figsize=(12, 10))
        sns.heatmap(matrix, annot=True, cmap="YlOrRd", fmt='.1f', 
                    xticklabels=list(ranks), yticklabels=list(ranks),
                    cbar_kws={'label': 'Open Raise %'})
        plt.title(f"Pre-flop Open Raise Percentage by Starting Hand - {position}")
        plt.xlabel("Second Card")
        plt.ylabel("First Card")
        plt.tight_layout()
        plt.show()
        
        heatmap_end_time = time.time()
        print(f"Heatmap for {position} generated in {heatmap_end_time - heatmap_start_time:.2f} seconds")
        print()

# Use raw strings for the folder path to avoid escape character issues in Windows paths
folder_path = r"C:\Users\leopa\AppData\Roaming\winamax\documents\accounts\1leolem1\history"
username = "1leolem1"

overall_start_time = time.time()
stats = generate_report(folder_path, username)
if stats:
    generate_heatmap(stats)
else:
    print("Unable to generate heatmap due to lack of data.")
overall_end_time = time.time()

print(f"Total script execution time: {overall_end_time - overall_start_time:.2f} seconds")