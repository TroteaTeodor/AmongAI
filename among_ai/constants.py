"""All game constants: map coordinates, rooms, tasks, vents, spawns, settings."""

# Display
WIDTH = 1920
HEIGHT = 1080
FPS = 60
TITLE = "Among AI"
TILESIZE = 32
GRIDWIDTH = WIDTH / TILESIZE
GRIDHEIGHT = HEIGHT / TILESIZE
FONT = 'Assets/Fonts/Rubik-ExtraBold.TTF'

# Colors (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKYBLUE = (135, 206, 235)
DARKGREY = (40, 40, 40)
LIGHTGREY = (100, 100, 100)
GREEN_COLOR = (0, 255, 0)
RED_COLOR = (255, 0, 0)
YELLOW_COLOR = (255, 255, 0)
ORANGE_COLOR = (255, 165, 0)
BROWN_COLOR = (106, 55, 5)
TRANSPARENT_BLACK = (0, 0, 0, 1)
MENU_FONT_COLOR = (255, 255, 255)
BGCOLOR = BROWN_COLOR

# Player
PLAYER_SPEED = 400
PLAYER_SPRITE_SIZE = (64, 86)

# Sprite layers
WALL_LAYER = 1
PLAYER_LAYER = 2
BOT_LAYER = 1
EFFECTS_LAYER = 3
ITEM_LAYER = 1

# Visual effects
LIGHT_MASK = 'light_350_med.png'
LIGHT_MASK_REACTOR = 'light_350_med_reactor.png'
NIGHT_COLOR = (20, 20, 20)
NIGHT_COLOR_REACTOR = (200, 20, 20)
LIGHT_RADIUS = (500, 500)
LIGHT_RADIUS_REACTOR = (500, 500)

# All player colors
ALL_COLOURS = [
    "Red", "Blue", "Orange", "Yellow", "Green",
    "Black", "Brown", "Pink", "Purple", "White"
]

# Display colors for chat/UI text per player colour
PLAYER_DISPLAY_COLORS = {
    "Red": (255, 50, 50),
    "Blue": (50, 100, 255),
    "Orange": (255, 165, 0),
    "Yellow": (255, 255, 50),
    "Green": (50, 255, 50),
    "Black": (100, 100, 100),
    "Brown": (139, 90, 43),
    "Pink": (255, 130, 180),
    "Purple": (160, 80, 220),
    "White": (230, 230, 230),
}

# Room definitions: name -> center coordinates
ROOMS = {
    "Cafeteria":      (3277, 658),
    "Medbay":         (2338, 1147),
    "Security":       (1806, 1279),
    "Reactor":        (880, 1474),
    "Upper Engine":   (1360, 699),
    "Lower Engine":   (1360, 2180),
    "Electrical":     (2425, 1950),
    "Storage":        (3175, 2308),
    "Admin":          (3920, 1775),
    "Communications": (3865, 2650),
    "Oxygen":         (4190, 1220),
    "Navigation":     (5405, 1340),
    "Weapons":        (4500, 600),
}

# Ambient sound detection radii per room
ROOM_AMBIENT_RADII = {
    "Cafeteria": 750,
    "Medbay": 450,
    "Security": 350,
    "Reactor": 450,
    "Upper Engine": 400,
    "Lower Engine": 400,
    "Electrical": 570,
    "Storage": 580,
    "Admin": 400,
    "Communications": 370,
    "Oxygen": 250,
    "Navigation": 300,
    "Weapons": 400,
}

# Vent locations (x, y)
VENT_LOCATIONS = [
    (3898, 791), (5309, 1144), (5309, 1525), (4513, 1525),
    (4531, 2459), (3694, 1942), (2220, 1711), (1580, 2407),
    (1887, 1578), (931, 1626), (802, 1151), (1586, 460),
    (2121, 1249), (4447, 363),
]

# Player spawn positions (Wider circle around Cafeteria table/button)
# Button is at approx (3284, 669). Table is roughly 200x200 centered there.
# Moving spawns to ~200px+ distance.
PLAYER_SPAWN_POSITIONS = [
    (3000, 670),  # Left
    (3550, 670),  # Right
    (3280, 450),  # Top
    (3280, 900),  # Bottom
    (3100, 500),  # Top-Left
    (3450, 500),  # Top-Right
]

# Bot spawn positions (Wider circle)
BOT_SPAWN_POSITIONS = [
    (3100, 850),  # Bottom-Left
    (3450, 850),  # Bottom-Right
    (3000, 600),  # Left side 2
    (3550, 600),  # Right side 2
    (3280, 400),  # Far Top
    (3280, 950),  # Far Bottom
    (2900, 670),  # Far Left
    (3650, 670),  # Far Right
    (3150, 900),
    (3400, 900),
]

# Task definitions: name -> {location, radius, duration_base, room}
TASK_DEFINITIONS = {
    "Stabilize Navigation": {
        "location": (5610, 1290),
        "radius": 140,
        "duration_base": 5.0,
        "room": "Navigation",
    },
    "Empty Garbage": {
        "location": (3940, 321),
        "radius": 70,
        "duration_base": 4.0,
        "room": "Cafeteria",
    },
    "Reboot Wifi": {
        "location": (3700, 1554),
        "radius": 50,
        "duration_base": 3.0,
        "room": "Admin",
    },
    "Fix Wiring": {
        "location": (3166, 1846),
        "radius": 50,
        "duration_base": 6.0,
        "room": "Electrical",
    },
    "Divert Power": {
        "location": (1031, 1216),
        "radius": 50,
        "duration_base": 4.0,
        "room": "Reactor",
    },
    "Align Engine": {
        "location": (1117, 837),
        "radius": 50,
        "duration_base": 5.0,
        "room": "Upper Engine",
    },
    "Fuel Engine": {
        "location_pickup": (3056, 2443),
        "location_deliver": (1226, 2300),
        "location": (3056, 2443),  # Primary location for pathfinding
        "radius": 50,
        "duration_base": 7.0,
        "room": "Storage",
    },
    "Clear Asteroids": {
        "location": (4513, 450),
        "radius": 250,
        "duration_base": 8.0,
        "room": "Weapons",
    },
}

# Total tasks to win
NUM_TASKS_TO_WIN = 8
NUM_BOTS = 9

# Key map locations for special interactions
EMERGENCY_BUTTON_POS = (3284, 669)
EMERGENCY_BUTTON_RADIUS = 250
GENERATOR_POS = (2472, 1721)
GENERATOR_RADIUS = 250
REACTOR_BUTTON_POS = (889, 999)
REACTOR_BUTTON_RADIUS = 250

# Sabotage fix locations
SABOTAGE_FIX_LIGHTS_POS = (2472, 1721)
SABOTAGE_FIX_LIGHTS_RADIUS = 50
SABOTAGE_FIX_REACTOR_POS = (889, 999)
SABOTAGE_FIX_REACTOR_RADIUS = 50

# Timer defaults (seconds)
KILL_COOLDOWN = 15
SABOTAGE_COOLDOWN = 15
REACTOR_MELTDOWN_TIME = 20
MEETING_DURATION = 30
MEETING_COOLDOWN = 15
LIGHTS_DURATION = 15
VENT_COOLDOWN_MS = 500

# Collision object names from TMX tilemap
COLLISION_OBJECT_NAMES = [
    'walls', 'tables', 'props', 'generator', 'medbay_comp',
    'engines', 'reactor', 'security_room_comp', 'admin_btn1', 'admin_btn2',
]

# Mouse buttons
LEFT_MOUSE_BUTTON = 1
MIDDLE_MOUSE_BUTTON = 2
RIGHT_MOUSE_BUTTON = 3

# Sound paths
BG_MUSIC = 'Ambience/AMB_Main.wav'
FOOTSTEP_SOUNDS = [f'Footsteps/Footstep0{i}.wav' for i in range(1, 9)]
STEPPING_RATE = 230

EFFECT_SOUNDS = {
    'main_menu_music': 'Background/main_menu_music.mp3',
    'start_game': 'General/roundstart.wav',
    'emergency_alarm': 'General/alarm_emergencymeeting.wav',
    'dead_body_found': 'General/report_Bodyfound.wav',
    'crises_alarm': 'General/crises.wav',
    'invisible': 'General/swap.wav',
    'vent': 'General/vent.wav',
    'victory_crew': 'General/victory_crew.wav',
    'victory_imposter': 'General/victory_impostor.wav',
    'game_left': 'General/victory_disconnect.wav',
    'fill_gas_can': 'General/gas_can_fill.wav',
    'pick_gas_can': 'General/pick_up_gas_can.wav',
    'menu_sel': 'UI/select.wav',
    'go_back': 'UI/back2.wav',
    'selected': 'UI/selected2.wav',
    'pause': 'UI/pause.wav',
    'backspace': 'UI/backspace.wav',
    'keypress': 'UI/keypress.wav',
    'map_click': 'UI/map_btn_click.wav',
    'task_completed': 'General/task_complete.wav',
    'imposter_kill_sound': 'Kill/imposter_kill.wav',
    'imposter_kill_cooldown_sound': 'Kill/imposter_kill_cooldown.wav',
    'imposter_kill_victim_sound': 'Kill/imposter_kill_victim.wav',
    'vote_sound': 'UI/votescreen_locking.wav',
}

AMBIENT_SOUNDS = {
    'admin_room': 'Ambience/AMB_Admin.wav',
    'cafeteria': 'Ambience/AMB_Cafeteria.wav',
    'cockpit': 'Ambience/AMB_Cockpit.wav',
    'comms3': 'Ambience/AMB_CommsRoom.wav',
    'electrical_room': 'Ambience/AMB_ElectricRoom.wav',
    'medbay_room': 'Ambience/AMB_MedbayRoom.wav',
    'u_engine_room': 'Ambience/AMB_EngineRoom.wav',
    'l_engine_room': 'Ambience/AMB_EngineRoom.wav',
    'reactor_room': 'Ambience/AMB_ReactorRoom.wav',
    'security_room': 'Ambience/AMB_SecurityRoom.wav',
    'storage_room': 'Ambience/AMB_Storage.wav',
    'oxygen_room': 'Ambience/AMB_Oxygen.wav',
    'weapons': 'Ambience/AMB_Weapons.wav',
    'main': 'Ambience/AMB_Main.wav',
}

ITEM_IMAGES = {
    'health': 'health_pack.png',
    'weapon': 'shotgun.png',
    'vent': 'ventilation.png',
    'emerg_btn': 'emergency_icon_inv.png',
}
