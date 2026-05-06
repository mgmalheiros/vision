import glob
import shutil
import random

random.seed(0)

files = glob.glob('labelme/*.jpg')
files = random.sample(files, k=100)
files.sort()

for file in files:
    shutil.move(file, 'pick')
    file = file.replace('.jpg', '.json')
    shutil.move(file, 'pick')
