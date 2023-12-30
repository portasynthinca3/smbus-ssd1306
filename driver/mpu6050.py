from smbus2 import SMBus, i2c_msg
from time import sleep
import numpy as np
import struct

class MPU6050Vals:
    SELF_TEST_X       = 0x0D
    SELF_TEST_Y       = 0x0E
    SELF_TEST_Z       = 0x0F
    SELF_TEST_A       = 0x10
    SAMPLE_RATE_DIV   = 0x19
    CONFIG_REG        = 0x1A
    GYRO_CONFIG       = 0x1B
    ACCEL_CONFIG      = 0x1C
    FIFO_EN           = 0x23
    INT_ENABLE        = 0x38
    ACCEL_OUT_BASE    = 0x3B
    TEMP_OUT_BASE     = 0x41
    GYRO_OUT_BASE     = 0x43
    USER_CTRL         = 0x6A
    PWR_MGMT_1        = 0x6B
    PWR_MGMT_2        = 0x6C

class MPU6050:
    def __init__(self, bus=0, addr=0x68):
        # set up interfacing
        self.bus = SMBus(bus)
        self.addr = addr

        # configure chip
        self.write_regs(MPU6050Vals.PWR_MGMT_1, [0b10000000]) # full reset
        sleep(0.1)
        self.write_regs(MPU6050Vals.PWR_MGMT_1, [0]) # disable sleep
        self.write_regs(MPU6050Vals.PWR_MGMT_2, [0]) # disable standby
        self.write_regs(MPU6050Vals.USER_CTRL, [0]) # disable FIFO, disable I2C master
        self.write_regs(MPU6050Vals.CONFIG_REG, [0]) # no ext. sync, LPF disabled
        self.write_regs(MPU6050Vals.SAMPLE_RATE_DIV, [0]) # 1 kHz
        self.write_regs(MPU6050Vals.FIFO_EN, [0]) # disable all FIFO inputs
        self.write_regs(MPU6050Vals.INT_ENABLE, [0]) # disable interrupts

        # perform self-test
        self.self_test()
    
        # further configuration
        self.write_regs(MPU6050Vals.CONFIG_REG, [7]) # no ext. sync, 10Hz LPF bandwidth
        self.set_full_scale(8, 250)
    
    def read_regs(self, start, cnt):
        read_op = i2c_msg.read(self.addr, cnt)
        self.bus.i2c_rdwr(
            i2c_msg.write(self.addr, [start]),
            read_op
        )
        return bytes(read_op)
    
    def write_regs(self, start, data):
        self.bus.i2c_rdwr(
            i2c_msg.write(self.addr, bytes([start]) + bytes(data))
        )

    def read_sensor_raw(self):
        raw_bytes = self.read_regs(MPU6050Vals.ACCEL_OUT_BASE, 14)
        accel_raw = np.array([struct.unpack(">hhh", raw_bytes[0:6])])
        (temp_raw,) = struct.unpack(">h", raw_bytes[6:8])
        gyro_raw = np.array([struct.unpack(">hhh", raw_bytes[8:14])])
        return accel_raw, gyro_raw, temp_raw
    
    def read_sensor(self):
        accel_raw, gyro_raw, temp_raw = self.read_sensor_raw()
        accel = accel_raw * self._full_scale[0] / 32768
        gyro = gyro_raw * self._full_scale[1] / 32768
        temp = (temp_raw / 340) + 36.53
        return accel, gyro, temp

    def set_full_scale(self, accel, gyro):
        self._full_scale = (accel, gyro)
        self.write_regs(MPU6050Vals.ACCEL_CONFIG, 0b11100000 | ({2: 0, 4: 1, 8: 2, 16: 3}[accel] << 3))
        self.write_regs(MPU6050Vals.GYRO_CONFIG, {250: 0, 500: 1, 1000: 2, 2000: 3}[gyro] << 3)

    def self_test(self):
        # read and parse test regs
        [st_x, st_y, st_z, st_a] = self.read_regs(MPU6050Vals.SELF_TEST_X, 4)
        gyro_test = (
            st_x & 0x1f,
            st_y & 0x1f,
            st_z & 0x1f,
        )
        accel_test = (
            ((st_x & 0xE0) >> 3) | ((st_a & 0x30) >> 4),
            ((st_y & 0xE0) >> 3) | ((st_a & 0x0C) >> 2),
            ((st_z & 0xE0) >> 3) | (st_a & 0x03),
        )

        # calculate FT (factory trim)
        gyro_ft = (
            0 if gyro_test[0] == 0 else 25 * 131 * (1.046 ** (gyro_test[0] - 1)),
            0 if gyro_test[1] == 0 else -25 * 131 * (1.046 ** (gyro_test[1] - 1)),
            0 if gyro_test[2] == 0 else 25 * 131 * (1.046 ** (gyro_test[2] - 1))
        )
        accel_ft = (
            0 if accel_test[0] == 0 else 4096 * 0.34 * ((0.92 / 0.34) ** ((accel_test[0] - 1) / 30)),
            0 if accel_test[1] == 0 else 4096 * 0.34 * ((0.92 / 0.34) ** ((accel_test[1] - 1) / 30)),
            0 if accel_test[2] == 0 else 4096 * 0.34 * ((0.92 / 0.34) ** ((accel_test[2] - 1) / 30))
        )
        ft = np.array([accel_ft, gyro_ft])

        # enable self-test
        self.write_regs(MPU6050Vals.ACCEL_CONFIG, [0b11110000]) # self test on all 3 axes, +/-8G range
        self.write_regs(MPU6050Vals.GYRO_CONFIG, [0b11100000]) # self test on all 3 axes, +/-250 deg/s range

        # read self-test data
        sleep(0.1)
        with_self_test = np.array(self.read_sensor_raw()[0:1])

        # disable self-test
        self.write_regs(MPU6050Vals.GYRO_CONFIG, [0])
        self.write_regs(MPU6050Vals.ACCEL_CONFIG, [0])

        # read non-self-test data
        sleep(0.1)
        wo_self_test = np.array(self.read_sensor_raw()[0:1])

        # calculate response
        self_test_response = with_self_test - wo_self_test
        change = (self_test_response - ft) / ft
        successful = (abs(change) <= 14).all()

        print(f"MPU6050 at 0x{self.addr:x} self-test: {'PASS' if successful else 'FAIL'}\nChange data:")
        print(change)
