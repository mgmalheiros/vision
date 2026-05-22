# Best practices

**1. Strip outputs before committing**
Notebook outputs (images, dataframes, tracebacks) bloat repos and create meaningless diffs. Clear all outputs before every commit — either manually or via automation.

**2. Use `.gitignore` wisely**
Ignore checkpoints and environment artifacts:
```
__pycache__/
.ipynb_checkpoints/
.venv/
uv.lock
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

# Tools

- **[nbdime](https://github.com/jupyter/nbdime)**: Semantic diffs/merges for notebooks; integrates with `git diff` and `git merge`
- **[nbstripout](https://github.com/kynan/nbstripout)**: Git filter that auto-strips outputs on `git add`; zero-friction setup

This gives clean commits (no outputs), readable diffs (semantic JSON diffing), and merge conflict resolution for notebooks.
