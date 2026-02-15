
import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame
    import yaml
except ImportError as e:
    print(f"Error: Missing dependencies. {e}")
    print("Please run: pip install -r requirements.txt")
    input("Press Enter to exit...")
    sys.exit(1)

from among_ai.config import Config
from among_ai.core.game_engine import GameEngine


def main():
    print("Starting AmongAI...")
    
    # Load configuration
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    try:
        config = Config.load(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # Initialize game engine
    game = GameEngine(config)
    
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nGame stopped by user.")
    except Exception as e:
        print(f"\nCritical Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
