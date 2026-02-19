
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

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from among_ai.config import Config
from among_ai.constants import WIDTH, HEIGHT, TITLE
from among_ai.core.game_engine import GameEngine
from among_ai.ui.menu import MainMenu


def main():
    print("Starting AmongAI...")

    # Load configuration
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    try:
        config = Config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # Initialize pygame once
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)

    try:
        while True:
            # Show main menu
            menu = MainMenu(screen, config)
            result = menu.run()

            if result.action == "quit":
                break

            # Config already updated by menu — launch game
            game = GameEngine(config, screen)
            try:
                game.run()
            except Exception as e:
                print(f"\nGame Error: {e}")
                import traceback
                traceback.print_exc()

            if game.quit_requested:
                break
    except KeyboardInterrupt:
        print("\nGame stopped by user.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
