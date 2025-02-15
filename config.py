DEBUG = False

# I2C settings
I2C_ADAPTER = 6
SSD1306_ADDR = 0x3C
MPU6050_ADDR = 0x68
BMP280_ADDR = 0x76
BATCH_CHUNK_SZ = 32 # keep halving this number if you get OSErrors nr 22

# Screen settings
# Fish tank
N_FISH = 10
N_SEAWEED = 7
# New year animation
MAX_SNOW = 150
# Power screen
BATTERY = "BAT1"
# Media screen
PLAYER_IGNORE = ["firefox"]
VOLUME_DEVICE = "default" # the list of devices is printed on startup
VOLUME_MULTIPLY = 4
# Load screen
SPEC_SMOOTH_SPEED = 4
TEMP_SENSOR = ("k10temp", "Tctl")

# Screen runner settings
MAX_UPDATE_RATE = 30
SCREEN_SWITCH_PERIOD = 5 # seconds
