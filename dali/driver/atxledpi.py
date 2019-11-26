from __future__ import print_function
from dali.command import Command
from dali.exceptions import CommunicationError
import dali.frame
import logging
import time
import serial
import struct

###############################################################################
# XXX: Adopt API to ``dali.driver.base``
###############################################################################

class AtxLEDPi(object):
    """Communicate with atxled.com Pi Hat
    (https://atxled.com/Pi)
    """

    def __init__(self, bus_prefix=""):
        self._bus_prefix = (bus_prefix)
        self._s = None

    def __enter__(self):
        self._s = serial.Serial( port ='/dev/ttyS0', baudrate = 19200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=.2 )
        return self

    def __exit__(self, *vpass):
        self._s.close()
        self._s = None

    def send(self, command):
        if self._s:
            s = self._s
        else:
            s = serial.Serial( port ='/dev/ttyS0', baudrate = 19200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=.2 )

        assert isinstance(command, Command)
        message = self._bus_prefix + 'h' + command.frame.pack.hex().upper() + '\n'

        logging.info(u"command: {}{}".format(
            command, " (twice)" if command.is_config else ""))

        # Set a default result which may be used if the first send fails
        result = "\x02\xff\x00\x00"

        print('Sending message: %s'%message)
        try:
            s.write(message.encode('utf-8'))
            result = s.read(4)
            if command.is_config:
                s.write(message.encode())
                result = s.read(4)
        except:
            raise
        finally:
            if not self._s:
                s.close()

        response = self.unpack_response(command, result)

        if response:
            logging.info(u"  -> {0}".format(response))

        return response

    def unpack_response(self, command, result):
        """Unpack result from the given bytestream and creates the
        corresponding response object

        :param command: the command which waiting for it's response
        :param result: the result bytestream which came back
        :return: the result object
        """

        assert isinstance(command, Command)

        response = None
        print('result(%d): %s\n============\n'%(struct.calcsize(result),result.hex().upper()))
        if struct.calcsize(result) != 4:
            ver, status, rval, pad = struct.unpack("BBBB", result)

            if command._response:
                if status == 0:
                    response = command._response(None)
                elif status == 1:
                    response = command._response(dali.frame.BackwardFrame(rval))
                elif status == 255:
                    # This is "failure" - daliserver seems to be reporting
                    # this for a garbled response when several ballasts
                    # reply.  It should be interpreted as "Yes".
                    response = command._response(dali.frame.BackwardFrameError(255))
                else:
                    raise CommunicationError("status was %d" % status)

        return response
