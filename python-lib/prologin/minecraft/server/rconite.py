"""Provides access to Valve rcon servers. For protocol details, see the
Valve developers wiki:
    https://developer.valvesoftware.com/wiki/Source_RCON_Protocol

Applications should generally call the ``connect`` function to obtain an
``RconClient`` object, then use the returned client's ``command`` method to
send commands to the server:

    import rconite

    with rconite.connect('locahost', 25575, 'password') as rcon:
        print rcon.command('help')

Protocol highlights:

* All integer values are sent as four-byte sequences, with the
least-signifigant byte first.
* Messages are framed. Each frame begins with a length field (an integer), and
contains exactly ``length`` bytes.
* Within a frame, the message payload has the following fields:
    * A request ID (an integer), used to correlate messages.
    * A type field (also an integer).
    * Two zero-terminated strings, in an unspecified but ASCII-compatible
    encoding.

rcon clients submit requests as messages whose types are either
``SERVERDATA_AUTH`` or ``SERVERDATA_EXECCOMMAND`` and receive responses as
messages whose types are either ``SERVERDATA_AUTH_RESPONSE`` or
``SERVERDATA_RESPONSE_VALUE``.

The only implementation I've actually tested this against is Minecraft; I've
no idea whatsoever whether this code works with Source-engine servers. If you
try it, let me know how it goes!
"""

import struct
import collections
import socket

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2

SERVERDATA_RESPONSE_VALUE = 0
SERVERDATA_AUTH_RESPONSE = 2

Message = collections.namedtuple('Message', [
    'request_id',
    'message_type',
    's1',
    's2'
])

def encode(request_id, message_type, s1, s2=b''):
    r"""Composes a single rcon message containing ``s1`` and (optionally)
    ``s2``. The returned byte string is suitable for framing, and does not
    contain a length field:

        >>> encode(1, SERVERDATA_EXECCOMMAND, 'kick angry-noob')
        '\x01\x00\x00\x00\x02\x00\x00\x00kick angry-noob\x00\x00'

    Note that ``s1`` and ``s2`` must not contain zero bytes:

        >>> encode(1, SERVERDATA_EXECCOMMAND, 'broken\x00value')
        Traceback (most recent call last):
            ...
        ValueError: data must not contain zero bytes

    This function is the inverse of ``decode``, and may be chained with it:

        >>> encode(*decode('\x01\x00\x00\x00\x02\x00\x00\x00kick angry-noob\x00\x00'))
        '\x01\x00\x00\x00\x02\x00\x00\x00kick angry-noob\x00\x00'
    """
    if b'\x00' in s1 or b'\x00' in s2:
        raise ValueError('data must not contain zero bytes')
    payload = b''.join([s1, b'\x00', s2, b'\x00'])
    return struct.pack('<2i', request_id, message_type) + payload

def decode(message):
    r"""Decomposes an rcon message into its constituent parts, returning a
    named tuple with ``request_id``, ``message_type``, ``s1``, and ``s2``
    fields corresponding to the message contents:

        >>> decode('\x01\x00\x00\x00\x02\x00\x00\x00kick angry-noob\x00\x00')
        Message(request_id=1, message_type=2, s1='kick angry-noob', s2='')

    If the rcon message is incomplete or malformed, decoding will raise a
    ``ValueError``:

        >>> decode('')
        Traceback (most recent call last):
            ...
        ValueError: incomplete message: ''
        >>> decode('\x01\x00\x00\x00\x02\x00\x00\x00')
        Traceback (most recent call last):
            ...
        ValueError: incomplete message: '\x01\x00\x00\x00\x02\x00\x00\x00'
        >>> decode(
        ...   '\x01\x00\x00\x00\x02\x00\x00\x00kick\x00\x00garbage'
        ... )
        Traceback (most recent call last):
            ...
        ValueError: trailing garbage in message: '\x01\x00\x00\x00\x02\x00\x00\x00kick\x00\x00garbage'

    This function is the inverse of ``decode``, and may be chained with it:

        >>> decode(encode(*Message(request_id=1, message_type=2, s1='kick angry-noob', s2='')))
        Message(request_id=1, message_type=2, s1='kick angry-noob', s2='')

    """
    try:
        request_id, message_type = struct.unpack('<2i', message[:8])
        s1, sep, remainder = message[8:].partition(b'\x00')
        if sep != b'\x00':
            raise ValueError('incomplete message: %r' % (message,))
        s2, sep, remainder = remainder.partition(b'\x00')
        if sep != b'\x00':
            raise ValueError('incomplete message: %r' % (message,))
        if remainder != b'':
            raise ValueError('trailing garbage in message: %r' % (message,))
        return Message(request_id, message_type, s1, s2)
    except struct.error:
        raise ValueError('incomplete message: %r' % (message,))

class RconChannel(object):
    """A transport for sequences of rcon messages. This maintains a connection
    to the server at ``host``:``port`` from the time it is created until the
    ``close`` method is called. (Alternately, ``RconChannel`` objects can be
    used as context managers, to ensure that they're automatically closed.)

    See the ``RconClient`` class for a more friendly interface to rcon.
    """
    def __init__(self, host, port):
        self.socket = socket.create_connection((host, port))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Releases the connection to the rcon server."""
        self.socket.close()

    def write_frame(self, frame):
        """Writes a single rcon frame to the server. The frame should be
        encoded as per the ``encode`` function. This method takes care of
        writing the frame header, containing the frame length.
        """
        frame_header = struct.pack('<i', len(frame))
        self._write_fully(frame_header + frame)

    def _write_fully(self, buffer):
        sent = 0
        while sent < len(buffer):
            sent += self.socket.send(buffer[sent:])

    def read_frame(self):
        """Reads a single rcon frame from the server. The returned string will
        not contain the frame header.
        """
        frame_header = self._read_fully(4)
        frame_length, = struct.unpack('<i', frame_header)
        return self._read_fully(frame_length)

    def _read_fully(self, length):
        read = b''
        while len(read) < length:
            data = self.socket.recv(length - len(read))
            if data == b'': # oops, premature end of stream
                raise EOFError('premature end of stream after %s of %s bytes' % (len(read), length))
            read += data
        return read

class RconError(Exception):
    """Base type for rcon client exceptions. ``RconError`` exceptions
    generally indicate that the connection is no longer viable and should be
    discarded.
    """

class AuthenticationError(RconError):
    """Raised when rcon authentication fails. The originating ``RconClient``
    should be considered invalid, and must be closed.
    """
    pass

class UnexpectedMessage(RconError):
    """Raised if a response message did not appear to match the request. The
    originating ``RconClient`` should be considered invalid, and must be
    closed.
    """
    pass

class RconClient(object):
    """Connects to an rcon server and carries commands and responses to and
    from the server. ``RconClient`` objects must be closed (using the
    ``close`` method) when no longer needed, to release the underlying network
    connection. (Alternately, ``RconClient`` objects can be used as context
    managers to ensure that they're closed automatically.)

    See the ``connect`` helper function, which automatically authenticates the
    newly-created connection.
    """
    def __init__(self, host, port, charset='utf8'):
        self.charset = charset
        self.channel = RconChannel(host, port)
        self.last_request_id = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Releases the connection to the rcon server."""
        self.channel.close()

    def authenticate(self, password):
        """Authenticates with the rcon server. If the server accepts the
        password, this method returns nothing; otherwise, it raises an
        ``AuthenticationError``; when this happens, the ``RconClient`` should
        be considered invalid, and must be closed.
        """
        self._converse(SERVERDATA_AUTH, password)

    def command(self, command):
        """Sends a single command to the rcon server, and returns the first
        response message's ``s1`` field. The ``s2`` field is ignored.
        """
        return self._converse(SERVERDATA_EXECCOMMAND, command)

    def _converse(self, type, s1):
        request_id = self._generate_request_id()
        message = encode(request_id, type, s1.encode(self.charset))
        self.channel.write_frame(message)
        response = decode(self.channel.read_frame())
        self._check_response_id(request_id, response)
        return response.s1.decode(self.charset)

    def _check_response_id(self, request_id, response):
        if response.request_id == -1:
            raise AuthenticationError('authentication failed')
        elif response.request_id != request_id:
            raise UnexpectedMessage('unexpected message from server: %r' % (
                response.s1,
            ))

    def _generate_request_id(self):
        self.last_request_id += 1
        return self.last_request_id

def connect(host, port, password, charset='utf8'):
    """Connects to an rcon server, returning an ``RconClient`` object if
    successful. The returned client will already have been authenticated.
    """
    client = RconClient(host, port, charset)
    try:
        client.authenticate(password)
        return client
    except RconError:
        client.close()
        raise
