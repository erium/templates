import os
# include css (needs --self-contained)
os.system("pandoc --self-contained -c ./css/data_quality_report.css data_quality_report.md -o data_quality_report.html")

filename = 'data_quality_report.html'
filename_backup = 'data_quality_report_backup.html'

# rename old file ans save as backup
if os.path.exists(filename):
    os.rename(filename, filename_backup)

# make new one that will contain modified code
with open(filename, 'w+'):
    pass

def convert_file_path(s):
    """converts relative path to absolute one"""
    s = s.replace(' ', '%20')
    path = os.getcwd()[13:] # Remove /home/jovyan
    s = s + '?download=inline'
    return s

import json
with open("artifacts/sample.json", "r") as outfile:
    data = json.load(outfile)

figures = [fig for _,fig in data['figures'].items()]

# absolute paths
abs_paths = [convert_file_path(_) for _ in figures]
# sort: global at the beginning
abs_paths_sorted = [p for p in abs_paths if 'global_pie.png' in p]
abs_paths_sorted = abs_paths_sorted + [p for p in abs_paths if not 'global_pie.png' in p]

# header for font
header = [
    '<!--',
    '/**',
    '* @license',
    '* MyFonts Webfont Build ID 280103',
    '* ',
    '* The fonts listed in this notice are subject to the End User License',
    '* Agreement(s) entered into by the website owner. All other parties are', 
    '* explicitly restricted from using the Licensed Webfonts(s).',
    '* ',
    '* You may obtain a valid license from one of MyFonts official sites.',
    '* http://www.fonts.com',
    '* http://www.myfonts.com',
    '* http://www.linotype.com',
    '*',
    '*/',
    '-->',
    '<link rel="stylesheet" type="text/css" href="./css/MyFontsWebfontsKit.css">',
    ''
]

if os.path.exists(filename_backup):
    with open(filename_backup, 'r') as old:
        lines = old.readlines()

with open(filename,'w') as new:
    # header 
    for l in header:
        new.write(l + '\n')
    counter = 0
    ignore = False
    for line in lines:
        if '</head>' in line:
            ignore = True
        elif '</header>' in line:
            ignore= False  
        elif '<img src=' in line:
            to_be_replaced_line = line
            split = to_be_replaced_line.split('"', 2)
            to_be_inserted_path = abs_paths_sorted[counter]
            line = split[0] + '"' + to_be_inserted_path + '"' + split[2]
            counter += 1

        if not ignore:
            new.write(line + '\n')

    


# remove backup
os.remove(filename_backup)


