import glob
import json
import os

for file in glob.glob('*.json'):
    with open(file, 'r', encoding='utf-8') as src:
        data = json.load(src)
        if 'imageData' in data:
            del data['imageData']

        new = file + '.new'
        with open(new, 'w', encoding='utf-8') as dst:
            json.dump(data, dst, indent=2)
        print(file)

        # copy times from the source file and apply to destination
        mtime = os.path.getmtime(file)
        atime = os.path.getatime(file)
        os.utime(new, (atime, mtime))
