#!/usr/bin/env python3
"""
RFID Card Setup Utility
Use this script to add, remove, and manage authorized RFID cards.
"""

import json
import sys
from pathlib import Path

def load_rfid_cards():
    """Load authorized RFID cards from file"""
    rfid_file = Path("authorized_rfid_cards.json")
    if rfid_file.exists():
        try:
            with open(rfid_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading RFID cards: {e}")
            return {}
    return {}

def save_rfid_cards(cards):
    """Save authorized RFID cards to file"""
    rfid_file = Path("authorized_rfid_cards.json")
    try:
        with open(rfid_file, 'w') as f:
            json.dump(cards, f, indent=2)
        print(f"✅ RFID cards saved to {rfid_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving RFID cards: {e}")
        return False

def list_cards(cards):
    """List all authorized RFID cards"""
    if not cards:
        print("📋 No authorized RFID cards found.")
        return
    
    print("📋 Authorized RFID Cards:")
    print("-" * 40)
    for card_id, card_name in cards.items():
        print(f"🏷️  {card_id} - {card_name}")
    print("-" * 40)
    print(f"Total: {len(cards)} cards")

def add_card(cards):
    """Add a new RFID card"""
    print("\n➕ Add New RFID Card")
    print("-" * 30)
    
    # Get card ID
    print("Please scan your RFID card or enter the 10-digit card ID:")
    try:
        card_id = input("Card ID (10 digits): ").strip()
        
        # Validate card ID
        if not card_id.isdigit():
            print("❌ Card ID must contain only digits")
            return False
        
        if len(card_id) < 8 or len(card_id) > 12:
            print("❌ Card ID must be 8-12 digits long")
            return False
        
        # Check if card already exists
        if card_id in cards:
            print(f"⚠️  Card {card_id} already exists: {cards[card_id]}")
            overwrite = input("Overwrite? (y/n): ").lower().startswith('y')
            if not overwrite:
                print("❌ Card addition cancelled")
                return False
        
        # Get card name
        card_name = input("Card name/description: ").strip()
        if not card_name:
            card_name = f"Card_{card_id}"
        
        # Add card
        cards[card_id] = card_name
        print(f"✅ Added card: {card_id} - {card_name}")
        return True
        
    except KeyboardInterrupt:
        print("\n❌ Card addition cancelled")
        return False
    except Exception as e:
        print(f"❌ Error adding card: {e}")
        return False

def remove_card(cards):
    """Remove an RFID card"""
    if not cards:
        print("📋 No cards to remove.")
        return False
    
    print("\n➖ Remove RFID Card")
    print("-" * 30)
    list_cards(cards)
    
    try:
        card_id = input("Enter card ID to remove: ").strip()
        
        if card_id in cards:
            card_name = cards[card_id]
            confirm = input(f"Remove '{card_id} - {card_name}'? (y/n): ")
            if confirm.lower().startswith('y'):
                del cards[card_id]
                print(f"✅ Removed card: {card_id} - {card_name}")
                return True
            else:
                print("❌ Removal cancelled")
        else:
            print(f"❌ Card {card_id} not found")
        return False
        
    except KeyboardInterrupt:
        print("\n❌ Removal cancelled")
        return False

def clear_all_cards(cards):
    """Clear all RFID cards"""
    if not cards:
        print("📋 No cards to clear.")
        return False
    
    print(f"\n🗑️  Clear All RFID Cards ({len(cards)} cards)")
    print("-" * 30)
    list_cards(cards)
    
    try:
        confirm = input("Are you sure you want to remove ALL cards? (yes/no): ")
        if confirm.lower() == 'yes':
            cards.clear()
            print("✅ All cards removed")
            return True
        else:
            print("❌ Clear operation cancelled")
        return False
        
    except KeyboardInterrupt:
        print("\n❌ Clear operation cancelled")
        return False

def test_rfid_reader():
    """Test RFID reader input"""
    print("\n🏷️  Test RFID Reader")
    print("-" * 30)
    print("Please scan an RFID card. The reader should input 10 digits automatically.")
    print("Press Ctrl+C to stop testing.")
    
    try:
        while True:
            user_input = input("Waiting for RFID scan: ")
            if user_input.strip():
                print(f"📥 Received: '{user_input}'")
                if user_input.isdigit() and 8 <= len(user_input) <= 12:
                    print("✅ Valid RFID format detected!")
                else:
                    print("⚠️  Format may not be correct (expected 8-12 digits)")
    except KeyboardInterrupt:
        print("\n🛑 RFID reader test stopped")

def main():
    """Main setup function"""
    print("🏷️  RFID Card Setup Utility")
    print("=" * 40)
    
    # Load existing cards
    cards = load_rfid_cards()
    
    while True:
        print("\n📋 Menu:")
        print("1. List authorized cards")
        print("2. Add new card")
        print("3. Remove card")
        print("4. Clear all cards")
        print("5. Test RFID reader")
        print("6. Save and exit")
        print("0. Exit without saving")
        
        try:
            choice = input("\nEnter choice (0-6): ").strip()
            
            if choice == '1':
                list_cards(cards)
            elif choice == '2':
                if add_card(cards):
                    save_rfid_cards(cards)
            elif choice == '3':
                if remove_card(cards):
                    save_rfid_cards(cards)
            elif choice == '4':
                if clear_all_cards(cards):
                    save_rfid_cards(cards)
            elif choice == '5':
                test_rfid_reader()
            elif choice == '6':
                save_rfid_cards(cards)
                print("👋 Setup complete!")
                break
            elif choice == '0':
                print("👋 Exiting without saving changes")
                break
            else:
                print("❌ Invalid choice. Please enter 0-6.")
                
        except KeyboardInterrupt:
            print("\n👋 Setup interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 