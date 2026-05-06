## Git + Jupyter Notebooks: Best Practices & Tools

### Core Problem

Jupyter notebooks (`.ipynb`) are JSON files that mix code, outputs, and metadata. This makes raw diffs noisy, merges painful, and history hard to read.

---

### Best Practices

**1. Strip outputs before committing**
Notebook outputs (images, dataframes, tracebacks) bloat repos and create meaningless diffs. Clear all outputs before every commit — either manually or via automation.

**2. Use `.gitignore` wisely**
Ignore checkpoints and OS/editor artifacts:
```
.ipynb_checkpoints/
__pycache__/
.DS_Store
```

**3. Keep notebooks focused and linear**
- One notebook = one logical task
- Avoid deeply nested logic; refactor reusable code into `.py` modules
- "Notebooks are for exploration; modules are for production"

**4. Commit frequently with meaningful messages**
Treat notebook commits like code commits — don't batch weeks of work into one save.

**5. Use a consistent execution order**
Always restart the kernel and run all cells top-to-bottom before committing. Non-linear execution state is a major source of reproducibility bugs.

**6. Separate notebooks by purpose**
Adopt a naming/folder convention like `01-eda.ipynb`, `02-modeling.ipynb` or `notebooks/exploratory/` vs `notebooks/reports/`.

---

### Popular Open Source Tools

#### Diff & Review
| Tool | What it does |
|---|---|
| **[nbdime](https://github.com/jupyter/nbdime)** | Semantic diffs/merges for notebooks; integrates with `git diff` and `git merge` |
| **[ReviewNB](https://www.reviewnb.com/)** | GitHub App for visual notebook diffs in PRs (free for public repos) |

#### Output Stripping / Pre-commit Hooks
| Tool | What it does |
|---|---|
| **[nbstripout](https://github.com/kynan/nbstripout)** | Git filter that auto-strips outputs on `git add`; zero-friction setup |
| **[pre-commit](https://pre-commit.com/)** + nbstripout | Hook-based automation; combine with other linters |
| **[nbconvert](https://nbconvert.readthedocs.io/)** | Convert notebooks to `.py`, HTML, PDF — useful for clean diffs via `--to script` |

#### Parameterization & Reproducibility
| Tool | What it does |
|---|---|
| **[Papermill](https://github.com/nteract/papermill)** | Execute notebooks with parameters; great for CI pipelines |
| **[Ploomber](https://github.com/ploomber/ploomber)** | Pipeline orchestration for notebooks with DAG-based dependency tracking |
| **[DVC](https://dvc.org/)** | Data Version Control — tracks datasets and model artifacts alongside code |

#### CI/CD Integration
| Tool | What it does |
|---|---|
| **[nbval](https://github.com/computationalmodelling/nbval)** | pytest plugin to validate notebook outputs haven't changed |
| **[pytest-notebook](https://github.com/chrisjsewell/pytest-notebook)** | Run and test notebooks as part of a test suite |
| **[repo2docker](https://github.com/jupyterhub/repo2docker)** | Build reproducible Docker images from a repo (used by Binder) |

---

### Recommended Minimal Setup

For most projects, this combination covers 90% of the friction:

```bash
# Install tools
pip install nbdime nbstripout pre-commit

# Register nbdime git drivers
nbdime config-git --enable --global

# Set up nbstripout as a git filter in the repo
nbstripout --install

# Add a pre-commit config (.pre-commit-config.yaml)
repos:
  - repo: https://github.com/kynan/nbstripout
    rev: 0.7.1
    hooks:
      - id: nbstripout
```

This gives you: clean commits (no outputs), readable diffs (semantic JSON diffing), and merge conflict resolution for notebooks.
