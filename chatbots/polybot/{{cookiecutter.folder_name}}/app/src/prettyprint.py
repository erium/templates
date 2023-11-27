class Colors():
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDCOLOR = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    INFO = OKBLUE
    WARNING = WARNING
    ERROR = FAIL
    SUCCESS = OKGREEN


class MessageType():
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


def prettyprint(msg: str | list, type: str = MessageType.INFO, max_len: int = 80, end: str = '\n'):
    """
    Prints log statements with colored type identifiers.

    Args:
        msg (str | list): Message. If string, separates entries by '\\n' or string length.
        type (str, optional): Message type. Defaults to MessageType.INFO.
        max_width (int, optional): Max length of the message in characters. Defaults to 79.
    """

    # create colored type identifier
    if type == MessageType.INFO:
        type = Colors.INFO + type + Colors.ENDCOLOR + ':' + ' ' * (9-len(type))
    elif type == MessageType.WARNING:
        type = Colors.WARNING + type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(type))
    elif type == MessageType.ERROR:
        type = Colors.ERROR + type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(type))
    elif type == MessageType.SUCCESS:
        type = Colors.SUCCESS + type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(type))
    else:
        type = Colors.INFO + type + Colors.ENDCOLOR + ':' + ' ' * (9-len(type))

    if isinstance(msg, list):
        msg = '\n'.join(msg)

    # split message into lines if '\n' is present
    if '\n' in msg:
        msg = msg.split('\n')
    else:
        msg = [msg]

    # split messages if longer then max_len
    for m, message in enumerate(msg):
        if len(message) > max_len:
            # split by word
            split_messages = message.split(' ')

            # build new messages
            shortened_messages = []
            short_message = ''
            for word in split_messages:
                if (len(short_message) + len(word) + 1) <= max_len:
                    short_message += word + ' '
                else:
                    shortened_messages.append(short_message)
                    short_message = word + ' '

            # add last message if not empty
            shortened_messages.append(short_message)
            # remove original message and insert split messages
            msg.pop(m)
            for s, shortened_message in enumerate(shortened_messages):
                msg.insert(m+s, shortened_message)

    for message in msg:
        # combine with message
        message = type + message
        print(message, end=end)


if __name__ == '__main__':
    prettyprint(msg='This is a test', type=MessageType.INFO)
    prettyprint(msg='This is a test', type=MessageType.WARNING)
    prettyprint(msg='This is a test', type=MessageType.ERROR)
    prettyprint(msg='This is a test', type=MessageType.SUCCESS)
    prettyprint(msg='This is a test\nwith multiple lines\nthis should be three messages',
                type=MessageType.ERROR)
    prettyprint(msg='Einmal lag in einer weit entfernten Galaxie ein Planet namens Zog. Auf Zog lebte ein kleiner, frecher Außerirdischer namens Fizz. Fizz war bekannt für seine Streiche und liebte es, seine Freunde zum Lachen zu bringen. Eines Tages beschloss Fizz, einen besonders großen Streich zu spielen. Er plante, die Kontrolle über das Raumschiff des Bürgermeisters zu übernehmen und es mit lila Tupfen zu bemalen. Er wusste, dass die Reaktion des Bürgermeisters unbezahlbar sein würde.')
