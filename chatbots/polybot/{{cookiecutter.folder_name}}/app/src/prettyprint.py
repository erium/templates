from typing import List

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


def prettyprint(msg: any, msg_type: str = MessageType.INFO, max_len: int = 80, end: str = '\n'):
    """
    Prints log statements with colored type identifiers.

    Args:
        msg (str | list): Message. If string, separates entries by '\\n' or string length.
        type (str, optional): Message type. Defaults to MessageType.INFO.
        max_width (int, optional): Max length of the message in characters. Defaults to 79.
    """

    # create colored type identifier
    if msg_type == MessageType.INFO:
        msg_type = Colors.INFO + msg_type + Colors.ENDCOLOR + ':' + ' ' * (9-len(msg_type))
    elif msg_type == MessageType.WARNING:
        msg_type = Colors.WARNING + msg_type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(msg_type))
    elif msg_type == MessageType.ERROR:
        msg_type = Colors.ERROR + msg_type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(msg_type))
    elif msg_type == MessageType.SUCCESS:
        msg_type = Colors.SUCCESS + msg_type + \
            Colors.ENDCOLOR + ':' + ' ' * (9-len(msg_type))
    else:
        msg_type = Colors.INFO + msg_type + Colors.ENDCOLOR + ':' + ' ' * (9-len(msg_type))

    # convert msg to str
    if not isinstance(msg, str):
        msg = str(msg)

    # embed into list
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
        message = msg_type + message
        print(message, end=end)


if __name__ == '__main__':
    # test colors
    prettyprint(msg='This is a test', msg_type=MessageType.INFO)
    prettyprint(msg='This is a test', msg_type=MessageType.WARNING)
    prettyprint(msg='This is a test', msg_type=MessageType.ERROR)
    prettyprint(msg='This is a test', msg_type=MessageType.SUCCESS)
    # test multiple lines
    prettyprint(msg='This is a test\nwith multiple lines\nthis should be three messages', msg_type=MessageType.ERROR)
    # test message splitting
    prettyprint(msg='Einmal lag in einer weit entfernten Galaxie ein Planet namens Zog. Auf Zog lebte ein kleiner, frecher Außerirdischer namens Fizz. Fizz war bekannt für seine Streiche und liebte es, seine Freunde zum Lachen zu bringen. Eines Tages beschloss Fizz, einen besonders großen Streich zu spielen. Er plante, die Kontrolle über das Raumschiff des Bürgermeisters zu übernehmen und es mit lila Tupfen zu bemalen. Er wusste, dass die Reaktion des Bürgermeisters unbezahlbar sein würde.')
    # test non-string objects
    prettyprint(dict(test="test", test2="test", test3="test", test4="test", test5="test", test6="test", test7="test", test8="test"))
    prettyprint([1, 2, 3, 4, 5], msg_type=MessageType.ERROR)
    prettyprint(prettyprint, msg_type=MessageType.SUCCESS)
