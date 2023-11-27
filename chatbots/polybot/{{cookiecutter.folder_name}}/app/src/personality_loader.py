import json
from pathlib import Path
from .prettyprint import prettyprint as pprint, MessageType as mt

def load_personalities(path: str) -> json:
    """
    Loads the personality.json and returns it as json object

    Returns:
        json: _description_
    """
    if Path(path).exists():
        with open(path, 'r') as f:
            p = json.load(f)
            return [p for p in p['personalities'].keys()]
    else:
        pprint('Personalities file not found.', type=mt.ERROR)