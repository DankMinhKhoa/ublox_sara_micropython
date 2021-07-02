from machine import UART, Pin, delay, micros, elapsed_micros
import utime

class CommandError(Exception):
    pass


class CommandFailure(Exception):
    pass

class ubloxSARA(object):

    # todo: maybe keep these in flash.
    AT_ENABLE_NETWORK_REGISTRATION = 'AT+CEREG=1'
    AT_ENABLE_SIGNALING_CONNECTION_URC = 'AT+CSCON=1'
    AT_ENABLE_POWER_SAVING_MODE = 'AT+NPSMR=1'
    AT_ENABLE_ALL_RADIO_FUNCTIONS = 'AT+CFUN=1'
    AT_REBOOT = 'AT+NRB'
    AT_CLOSE_SOCKET = 'AT+NSOCL'
    AT_GET_IP = 'AT+CGPADDR'
    AT_SEND_TO = 'AT+NSOST'
    AT_CHECK_CONNECTION_STATUS = 'AT+CSCON?'
    AT_RADIO_INFORMATION = 'AT+NUESTATS="RADIO"'
    DEFAULT_BANDS = [20]
    AT_CREATE_UDP_SOCKET = 'AT+USOCR=17'
    AT_CREATE_TCP_SOCKET = 'AT+USOCR=6'
    AT_ENABLE_LTE_M_RADIO = 'AT+URAT=7'
    AT_ENABLE_NBIOT_RADIO = 'AT+URAT=8'
    AT_CLOSE_SOCKET = 'AT+USOCL'
    AT_REBOOT = 'AT+CFUN=15'  # R4 specific
    REBOOT_TIME = 10
    SUPPORTED_SOCKET_TYPES = ['UDP', 'TCP']
    SUPPORTED_RATS = {'NBIOT': AT_ENABLE_NBIOT_RADIO,
                      'LTEM': AT_ENABLE_LTE_M_RADIO}

    def __init__(self, uart, baudRate=115200, powerPin = None, statusPin = None, resetPin = None):
        """Initialize this module. uart may be an integer or an instance 
        of machine.UART. baudRate can be used to set the Baud rate for the 
        serial communication. 
        Optional power pin specified will perform a power cycle at init
        Optional status pin connected to GPIO1 of SARA module provides network readiness
        Optional reset pin"""
        if uart:
            if type(uart) is int:
                self.uart = UART(uart, baudRate)
            elif type(uart) is UART:
                self.uart = uart
            else:
                raise Exception("Argument 'uart' must be an integer or pyb.UART object!")
        else:
            raise Exception("Argument uart must not be 'None'!")
        
        if powerPin:
            self.powerPin = Pin(powerPin, Pin.OUT_PP)
            pass
        else: 
            raise Exception("Argument uart must not be 'None'!")


    def _send_command(self, cmd, timeout=0, debug=False):
        """Send a command to the SARA module over UART and return the 
        output.
        After sending the command there is a 1 second timeout while 
        waiting for an answer on UART. For long running commands (like AP 
        scans) there is an additional 3 seconds grace period to return 
        results over UART.
        Raises an CommandError if an error occurs and an CommandFailure 
        if a command fails to execute."""
        if debug:
            start = micros()
        cmd_output = []
        okay = False
        if cmd == '' or cmd == b'':
            raise CommandError("Unknown command '" + cmd + "'!")
        # AT commands must be finalized with an '\r\n'
        cmd += '\r\n'
        if debug:
            print("%8i - TX: %s" % (elapsed_micros(start), str(cmd)))
        self.uart.write(cmd)
        # wait at maximum one second for a command reaction
        cmd_timeout = 100
        while cmd_timeout > 0:
            if self.uart.any():
                cmd_output.append(self.uart.readline())
                if debug:
                    print("%8i - RX: %s" % (elapsed_micros(start), str(cmd_output[-1])))
                if cmd_output[-1].rstrip() == b'OK':
                    if debug:
                        print("%8i - 'OK' received!" % (elapsed_micros(start)))
                    okay = True
                delay(10)
            cmd_timeout -= 1
        if cmd_timeout == 0 and len(cmd_output) == 0:
            if debug == True:
                print("%8i - RX timeout of answer after sending AT command!" % (elapsed_micros(start)))
            else:
                print("RX timeout of answer after sending AT command!")
        # read output if present
        while self.uart.any():
            cmd_output.append(self.uart.readline())
            if debug:
                print("%8i - RX: %s" % (elapsed_micros(start), str(cmd_output[-1])))
            if cmd_output[-1].rstrip() == b'OK':
                if debug:
                    print("%8i - 'OK' received!" % (elapsed_micros(start)))
                okay = True
        # handle output of AT command 
        if len(cmd_output) > 0:
            if cmd_output[-1].rstrip() == b'ERROR':
                raise CommandError('Command error!')
            elif cmd_output[-1].rstrip() == b'OK':
                okay = True
            elif not okay:
                # some long running commands do not return OK in case of success 
                # and/or take some time to yield all output.
                if timeout == 0:
                    cmd_timeout = 300
                else:
                    if debug:
                        print("%8i - Using RX timeout of %i ms" % (elapsed_micros(start), timeout))
                    cmd_timeout = timeout / 10
                while cmd_timeout > 0:
                    delay(10)
                    if self.uart.any():
                        cmd_output.append(self.uart.readline())
                        if debug:
                            print("%8i - RX: %s" % (elapsed_micros(start), str(cmd_output[-1])))
                        if cmd_output[-1].rstrip() == b'OK':
                            okay = True
                            break
                        elif cmd_output[-1].rstrip() == b'FAIL':
                            raise CommandFailure()
                    cmd_timeout -= 1
            if not okay and cmd_timeout == 0 and debug:
                print("%8i - RX-Timeout occured and no 'OK' received!" % (elapsed_micros(start)))
        return cmd_output
