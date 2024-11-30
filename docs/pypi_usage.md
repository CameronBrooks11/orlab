# How to Upload to Test PyPI and PyPI

This guide explains how to upload your Python package to Test PyPI (for testing) and then to the official PyPI.

## Steps

1. **Install Required Tools**
   ```
   pip install build twine
   ```

2. **Build the Distribution Files**
   ```
   python -m build
   ```

   This creates a `dist/` directory with `.tar.gz` and `.whl` files.

3. **Upload to Test PyPI**
   ```
   twine upload --repository testpypi dist/*
   ```

   Use your Test PyPI credentials or API token. You can test the package with:
   ```
   pip install -i https://test.pypi.org/simple/ your-package-name
   ```

4. **Upload to PyPI**
   After testing, upload to the official PyPI:
   ```
   twine upload dist/*
   ```

   Use your PyPI credentials or API token.

5. **Verify Installation**
   Install the package from PyPI to ensure it works:
   ```
   pip install your-package-name
   ```

## Notes
- Use a [PyPI API token](https://pypi.org/help/#apitoken) for secure uploads.
- Ensure `README.md` renders correctly on PyPI by testing locally:
  ```
  pip install readme_renderer
  python setup.py check -r -s
  ```
