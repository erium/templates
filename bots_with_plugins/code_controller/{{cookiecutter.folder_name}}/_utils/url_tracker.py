import json
import os
from pathlib import Path


class UrlTracker:

    def __init__(self, runner_id: str = os.getenv('HALERIUM_ID'), port: int = 8498, path: str = '', board: dict = {}):
        self.runner_id = runner_id
        self.port = port
        self.path = path
        self.board = board

    def _store_card_ids_url_map(self) -> dict:
        """
        Stores the card IDs and their URLs in a dictionary.

        Args:
            board (dict): The board.

        Returns:
            dict: A dictionary containing the card IDs and their URLs.
        """

        card_ids_url_map = {}
        if self.board:
            try:
                for card in self.board['nodes']:
                    if card['type'] == 'note':
                        card_ids_url_map[card['id']] = json.loads(card['type_specific']
                                                                  ['message']).get('endpoint')['url']
            except json.JSONDecodeError:
                print(f'Coud not decode board. Make sure it is a valid JSON.')

        elif self.path:
            try:
                boards = Path(self.path).glob('*.board')

                for b in boards:
                    with open(b, 'r') as f:
                        b_json = json.load(f)

                    for card in b_json['nodes']:
                        if card['type'] == 'note' and str(card['title']).startswith('Function: '):
                            card_ids_url_map[card['id']] = json.loads(card['type_specific']
                                                                      ['message']).get('endpoint')['url']
            except json.JSONDecodeError:
                print(
                    f'Could not decode board {b}. Make sure it is a valid JSON.')

        with open('.card_ids_url_map.json', 'w') as f:
            json.dump(card_ids_url_map, f, indent=4, ensure_ascii=False)

        print('Card IDs and URLs stored in .card_ids_url_map.json')
        # return card_ids_url_map

    def _update_endpoint_urls(self) -> list:
        """
        Finds all function cards by their ID.

        Args:
            board (dict): A Halerium board.

        Returns:
            dict: The updated board.
        """
        with open('.card_ids_url_map.json', 'r') as f:
            card_ids_url_map: dict = json.load(f)

        # generate new urls
        new_card_ids_url_map = {}
        for id, url in card_ids_url_map.items():
            new_url = f'{os.getenv("HALERIUM_BASE_URL")}/apps/{self.runner_id}/{str(url).split("/")[-2]}/{str(url).split("/")[-1]}'
            new_card_ids_url_map[id] = new_url

        # get board files
        if Path(self.path).exists():
            boards = Path(self.path).glob('*.board')

            for b in boards:
                with open(b, 'r') as f:
                    board = json.load(f)

                # update board
                for idx, card in enumerate(board['nodes']):
                    if card['id'] in new_card_ids_url_map.keys():
                        message = json.loads(card['type_specific']['message'])
                        message['endpoint']['url'] = new_card_ids_url_map[card['id']]
                        card['type_specific']['message'] = json.dumps(message)
                        board['nodes'][idx] = card

                # export board
                with open(b, 'w') as f:
                    json.dump(board, f, indent=4, ensure_ascii=False)
                
                print(f'Updated {b.name}')

        else:
            print(f'Path {self.path} does not exist.')

        # update the id -> url map file
        with open('.card_ids_url_map.json', 'w') as f:
            json.dump(new_card_ids_url_map, f, indent=4, ensure_ascii=False)

        print('Endpoint URLs updated.')
        print('Please refresh the page for the changes to become effective.')
        # return board


if __name__ == '__main__':
    # runner_id
    runner_id = os.getenv('HALERIUM_ID')

    # update endpoint URLs
    ut = UrlTracker(runner_id=runner_id, path='boards')
    # generate id -> url map
    ut._store_card_ids_url_map()

    # update endpoint URLs
    ut._update_endpoint_urls()
