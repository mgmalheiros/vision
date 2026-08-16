"""
Shared helpers for the object-counting notebooks (process/counting/*.ipynb).

Every 2-processing-*.ipynb notebook imports this module the same way:

    import common

Locally this works because Jupyter puts a notebook's own directory on
sys.path, and process/counting/common.py sits right next to the notebooks.
On Google Colab, the "Colab-specific setup" cell of each notebook downloads
this file into the working directory before it is imported, so the same
`import common` line works unchanged in both places.

This module intentionally has no notion of "datasets" vs "Colab" — it only
deals with data that has already been prepared and downloaded to disk by the
calling notebook (see 1-preparation.ipynb).
"""

import io
import time
import tracemalloc
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from skimage import io as skio
from skimage import util as skutil


# ---------------------------------------------------------------------------
# Prepared-dataset loading
# ---------------------------------------------------------------------------

def load_prepared_images(zip_path):
    """Read every image in a *prepared* ZIP file into memory.

    Returns a dict {name: image}, ordered the same way the ZIP was written
    (which 1-preparation.ipynb makes deterministic), where `name` is the
    file name without its extension and `image` is a uint8 grayscale ndarray.
    """
    images = {}
    with zipfile.ZipFile(zip_path, 'r') as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
        for entry in names:
            data = io.BytesIO(archive.read(entry))
            image = skio.imread(data)
            image = skutil.img_as_ubyte(image)
            name = entry.rsplit('/', 1)[-1].rsplit('.', 1)[0]
            images[name] = image
    return images


def load_labels(csv_path):
    """Load the labels.csv produced by 1-preparation.ipynb.

    Columns: name, labels (comma-joined raw annotation labels),
    real_count (ground-truth object count, 'finger' already excluded).
    """
    return pd.read_csv(csv_path)


def real_count(df, name):
    """Ground-truth object count for image `name`, as a plain int.

    Raises KeyError if `name` is not present in `df`, which is preferable
    to silently returning 0: a missing row usually means the images and
    labels ZIPs are out of sync and that is worth noticing.
    """
    row = df.loc[df['name'] == name, 'real_count']
    if row.empty:
        raise KeyError(f"no labels row for image {name!r}")
    return int(row.iloc[0])


# ---------------------------------------------------------------------------
# Plotting shortcuts (v1.3) — shared verbatim across all counting notebooks
# ---------------------------------------------------------------------------

def P(a=False, title='', size=2, axis=False, cmap='inferno', interpolation='bilinear', bins=False, fontsize=12, dpi=75):
    global FIG
    if 'FIG' not in globals():
        # first subplot
        FIG = plt.figure(figsize=(size, size), dpi=dpi)
        ax = FIG.add_subplot(1, 1, 1)
    else:
        # change the geometry and add a new subplot
        n = len(FIG.axes)
        FIG.set_figwidth(FIG.get_figheight() * (n + 1))
        gs = FIG.add_gridspec(1, n + 1)
        for i in range(n):
            FIG.axes[i].set_subplotspec(gs[i])
        ax = FIG.add_subplot(gs[-1])

    ax.axis(axis)
    if title: ax.set_title(title)
    if type(a) == bool: pass
    elif type(a) == np.ndarray and bins != False:
        ax.hist(a.ravel(), bins=bins)
        ax.set_aspect(np.diff(ax.get_xlim())[0] / np.diff(ax.get_ylim())[0])
    elif type(a) == np.ndarray and a.ndim == 2: ax.imshow(a, cmap=cmap, interpolation=interpolation)
    elif type(a) == np.ndarray and a.ndim == 3: ax.imshow(a, interpolation=interpolation)
    elif type(a) == str: ax.text(0, 0, a, fontsize=fontsize, fontfamily='monospace')
    else: ax.plot(a)


def S():
    global FIG
    if 'FIG' in globals(): plt.show(); del FIG


def V(*args, **kwargs):
    P(*args, **kwargs); S()


# ---------------------------------------------------------------------------
# Evaluation harness
# ---------------------------------------------------------------------------
#
# Every technique notebook defines its own `detect_xxx(image) -> int` and
# then calls `evaluate_method` on the *whole* prepared dataset once it is
# happy with a few visual spot checks. This gives every notebook the same
# accuracy / time / memory columns, which is what the PIC project's
# "framework" ultimately needs to compare classical vs. ML-based techniques
# on equal footing (see objective 5 in the project proposal).
#
# Memory is measured with `tracemalloc`, which tracks Python- and
# NumPy-attributed allocations (NumPy registers its allocator with
# tracemalloc). It will NOT see memory allocated by lower-level C libraries
# that bypass NumPy's allocator, so treat `peak_memory_kb` as a consistent,
# comparable *proxy* across techniques rather than an exact RSS reading.

def evaluate_method(images, df, detect_fn, method_name, parameters=None, results_path=None):
    """Run `detect_fn` over every image in `images`, score it against the
    ground truth in `df`, and optionally persist the results as YAML.

    Parameters
    ----------
    images : dict {name: image}, as returned by load_prepared_images
    df : labels dataframe, as returned by load_labels
    detect_fn : callable(image) -> int
    method_name : short human-readable name, e.g. "Canny edges"
    parameters : dict of hyperparameters used by detect_fn (for the record)
    results_path : where to write "<method>_results.yaml"; skipped if None

    Returns
    -------
    (results, summary): a per-image pandas DataFrame and a summary dict.
    """
    rows = []
    for name, image in images.items():
        gt = real_count(df, name)

        tracemalloc.start()
        t0 = time.perf_counter()
        detected = int(detect_fn(image))
        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rows.append({
            'image': name,
            'real_count': gt,
            'detected_count': detected,
            'abs_error': abs(detected - gt),
            'correct': detected == gt,
            'time_seconds': elapsed,
            'peak_memory_kb': peak / 1024,
        })

    results = pd.DataFrame(rows)

    summary = {
        'method': method_name,
        'parameters': parameters or {},
        'n_images': int(len(results)),
        'accuracy': float(results['correct'].mean()),
        'mean_absolute_error': float(results['abs_error'].mean()),
        'mean_time_seconds': float(results['time_seconds'].mean()),
        'mean_peak_memory_kb': float(results['peak_memory_kb'].mean()),
    }

    if results_path is not None:
        payload = {'summary': summary, 'per_image': results.to_dict(orient='records')}
        with open(results_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)

    return results, summary
