# smbus-ssd1306
Why not use an SSD1306 OLED module as a metadata display for my laptop? That's exactly what I thought and that's exactly how this project came to be. It's intended to control an SSD1306 display connected straight to the System Management Bus, or SMBus for short.\
**Warning:** Linux-only!

## Current screens
  1. CPU frequency, CPU load graph, RAM usage, RAM usage graph
  2. CPU package temperature, CPU temp graph, network download speed, net graph
  3. Media playback: song title, artist, auto-rating, time, song length

## Setup
  1. Acquire an SSD1306 module that's wired to use the I2C interface
  2. Find a schematic (and, preferably, a boardview) for your motherboard
  3. Find a convenient place to connect to the system SMB interface. The interface consists of two data lines: SDA (or DAT) and SCL (or CLK). My motherboard has three SMB interfaces coming out of the PCH, so I found the main one. There is also a whole host of other I2C interfaces you may find on your board. I tried some of them, but `i2cdetect` wasn't able to detect the display on any of them.
  4. Trace the schematic and make sure that these two lines are pulled up with a (probably 4.7kOhm) resistor to 3.3V as that's the voltage level the display is expecting.
  5. Find a power rail to power the display with. Those convenient blue modules feature an onboard 5V-to-3.3V charge pump, so if you're using one find a 5V rail. Otherwise find a 3.3V power rail. **Note:** some power rails are labeled `SUS`, which stands for "suspend". You probably don't want to use them as they're active even while the computer is powered down.
  6. Connect your display to those pins.
  7. Run `i2cdetect 0` (from the `i2c-tools` package on most distros) and check if it has found a device at address `0x3C` or `0x3D` - that's the display address. If not:\
    1. run `i2cdetect -l` to list all I2C adapters, try all of them and see if the display shows up on any of them;\
    2. check your wiring and try again.
  8. Tweak the configuration in `main.py` (see below)
  9. Change the adapter virtual file ownership: `chown $USER /dev/i2c-0` (or `i2c-{the_adapter_id_that_worked_in_step_7}`). You'll probably need to do this at startup.
  10. Run! `python3 main.py` or `chmod +x main.py && ./main.py`

## Configuration
Look in `main.py` for these variables
  - `I2C_ADAPTER`: adapter number. Probably 0, but may be something else. Please refer to step 7 in `Setup`
  - `SSD1306_ADDR`: display address. Probably `0x3C`, but may also be `0x3D`
  - `SCREEN_SWITCH_PERIOD`: the display will switch between different screens that many seconds apart
  - `MEDIA_PROVIDER`: application to grab media playback data from using D-Bus