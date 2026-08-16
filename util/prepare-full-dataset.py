"""
Reorganizes the full "regression" dataset (6021 images) downloaded from
https://ieee-dataport.org/open-access/brazilian-coin-detection-dataset into the
same two-ZIP layout as datasets/1-coins-small-*.zip, so it can be used as
`dataset_size = 'full'` in 1-preparation.ipynb.

The downloaded ZIP has every .jpg/.json flat inside a single top-level folder
(e.g. "regression/5_1477290516.jpg", "regression/5_1477290516.json" -- adjust
SOURCE_PREFIX below if yours differs). This script does not read images or
JSON contents, only re-packages the same bytes under the project's naming
convention, so it runs in a few seconds regardless of dataset size.

Usage: edit SOURCE_ZIP below, then run from the repository root:
    python util/prepare-full-dataset.py

Output (both gitignored, see .gitignore):
    datasets/1-coins-full-image.zip
    datasets/1-coins-full-annot.zip
"""

import pathlib
import zipfile

SOURCE_ZIP = pathlib.Path('regression.zip').expanduser()
SOURCE_PREFIX = 'regression/'  # top-level folder inside SOURCE_ZIP, see docstring

DATASET_NAME = '1-coins-full'
OUTPUT_IMAGE_ZIP = pathlib.Path('datasets') / f'{DATASET_NAME}-image.zip'
OUTPUT_ANNOT_ZIP = pathlib.Path('datasets') / f'{DATASET_NAME}-annot.zip'

date_time = (1980, 1, 1, 0, 0, 0)  # ensure all zip entries have the same time

OUTPUT_IMAGE_ZIP.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(SOURCE_ZIP, 'r') as src:
    names = sorted(n for n in src.namelist() if n.startswith(SOURCE_PREFIX))
    image_names = [n for n in names if n.lower().endswith('.jpg')]
    annot_names = [n for n in names if n.lower().endswith('.json')]

    print(f'{SOURCE_ZIP.name}: {len(image_names)} images, {len(annot_names)} annotations')

    with zipfile.ZipFile(OUTPUT_IMAGE_ZIP, 'w') as dst:
        for name in image_names:
            output_name = f'{DATASET_NAME}/{pathlib.Path(name).name}'
            dst.writestr(zipfile.ZipInfo(output_name, date_time=date_time), src.read(name))

    with zipfile.ZipFile(OUTPUT_ANNOT_ZIP, 'w') as dst:
        for name in annot_names:
            output_name = f'{DATASET_NAME}/{pathlib.Path(name).name}'
            dst.writestr(zipfile.ZipInfo(output_name, date_time=date_time), src.read(name))

print(f'wrote {OUTPUT_IMAGE_ZIP} and {OUTPUT_ANNOT_ZIP}')
