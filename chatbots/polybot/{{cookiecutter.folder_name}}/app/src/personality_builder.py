from prettyprint import prettyprint as pprint, MessageType as mt
import json
import os
from pathlib import Path

class Personalities():

    def __init__(self, file_name: str = 'personalities', file_type: str = 'json'):
        self.export_path = Path('../../assets/personalities')
        self.file_name = file_name
        self.file_type = file_type

        # make sure in correct cwd
        cwd = Path().cwd().name
        if not cwd == 'src':
            pprint(f'Currently in wrong working directory ({cwd}). Attempting to change automatically...', type=mt.WARNING)
            if cwd == 'polybot':
                p = Path('app/code/src')
                os.chdir(p)
                pprint('Changed to src successfully!', type=mt.SUCCESS)

            else:
                pprint('Could not change to utils automatically. Please change your current directory to the "utils" directory and execute this code again.', type=mt.ERROR)
                exit()
            
    
    def _export(self, d: dict):
        with open(self.export_path / ".".join([self.file_name, self.file_type]), 'w') as f:
            json.dump(d, f, indent=4)
            pprint(f'Created and exported json. Personalities: {[p for p in d["personalities"]]}', type=mt.SUCCESS)


    def create(self, name: str, sys_prompt: str):
        try:
            with open(self.export_path / ".".join([self.file_name, self.file_type]), 'r') as f:
                j = json.load(f)
                ps = j['personalities']
                ps[name] = sys_prompt
                d = {'personalities': ps}
                self._export(d)
        except FileNotFoundError as e:
            pprint('Personalities.json not found. Setting it up for you now.', type=mt.WARNING)
            with open(self.export_path / ".".join([self.file_name, self.file_type]), 'w') as f:
                json.dump({'personalities': {}}, f)
            self.create(name, sys_prompt)

    
    def remove(self, name: str):
        try:
            with open(self.export_path / ".".join([self.file_name, self.file_type]), 'r') as f:
                j = json.load(f)
                ps = j['personalities']
                popped = ps.pop(name)
                d = {'personalities': ps}
                self._export(d)
                
        except FileNotFoundError as e:
            pprint('Personalities.json not found. Could not remove personality.', type=mt.ERROR)

    
    def peek(self):
        try:
            with open(self.export_path / ".".join([self.file_name, self.file_type]), 'r') as f:
                j = json.load(f)
                pprint(f'Current Personalities: {[[key, value] for key, value in j["personalities"].items()]}', type=mt.INFO)


        except FileNotFoundError as e:
            pprint('Personalities.json not found', type=mt.ERROR)


if __name__ == "__main__":
    p = Personalities()
    def manipulate_personalities():
        mode = input("[C]reate, [R]emove, or [S]ee a personality? (press CTRL+C to end this program)\n> ")
        if mode.lower() == 'c':
            name = input("Personality name:\n> ")
            sys_prompt = input("Personality system prompt:\n> ")
            p.create(name, sys_prompt)
        elif mode.lower() == 'r':
            name = input("Personality name:\n> ")
            p.remove(name)
        elif mode.lower() == 's':
            p.peek()

        manipulate_personalities()
    
    manipulate_personalities()    