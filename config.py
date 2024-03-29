DEBUG = True

# I2C settings
I2C_ADAPTER = 3
SSD1306_ADDR = 0x3C
MPU6050_ADDR = 0x68
BMP280_ADDR = 0x76
BATCH_CHUNK_SZ = 32 # max number of I2C transactions per syscall. Lower this number if you get OSErrors nr 22

# Screen settings
# New year animation
MAX_SNOW = 150
# Power screen
BATTERY = "BAT1"
# Media screen
VOLUME_DEVICE = "default" # the list of devices is printed on startup
VOLUME_MULTIPLY = 4

# Screen runner settings
MAX_UPDATE_RATE = 60
SCREEN_SWITCH_PERIOD = 5 # seconds
