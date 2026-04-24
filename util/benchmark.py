import glob
import io
import time
import zipfile
import skimage

# from google.colab import drive
# drive.mount('/content/drive')

archive  = '1_coins.zip'

t0 = time.perf_counter()
with zipfile.ZipFile(archive, 'r') as zip:
    for filename in zip.namelist():
        # print(filename)
        data = io.BytesIO(zip.read(filename))
        image = skimage.io.imread(data, as_gray=True)
        image = skimage.util.img_as_ubyte(image)
t1 = time.perf_counter()
print(f"   zip time: {t1 - t0:.4f} s")

folder  = '1_coins/'

files = glob.glob(folder + '*.jpg')
t0 = time.perf_counter()
for file in files:
  image = skimage.io.imread(file, as_gray=True)
  image = skimage.util.img_as_ubyte(image)
t1 = time.perf_counter()
print(f"folder time: {t1 - t0:.4f} s")
