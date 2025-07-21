# PyPI Publishing Instructions for FlakeRadar v1.1.0

## 🔐 Authentication Setup

You need to set up PyPI authentication to publish the package. Here are your options:

### Option 1: API Token (Recommended)

1. **Get your PyPI API token**:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token for this project
   - Copy the token (starts with `pypi-...`)

2. **Set up authentication using environment variables**:
   ```bash
   export TWINE_USERNAME="__token__"
   export TWINE_PASSWORD="pypi-your-token-here"
   ```

3. **Or create/update ~/.pypirc**:
   ```ini
   [pypi]
   username = __token__
   password = pypi-your-token-here
   ```

### Option 2: Interactive Authentication

Run the upload command and enter your credentials when prompted:
```bash
python -m twine upload dist/flakeradar-1.1.0* --username __token__
# Enter your API token when prompted for password
```

## 📦 Publishing Commands

Once authentication is set up, run:

```bash
# Verify package integrity
python -m twine check dist/flakeradar-1.1.0*

# Upload to PyPI
python -m twine upload dist/flakeradar-1.1.0*
```

## 🧪 Verification After Publishing

Once published, verify the installation:

```bash
# Install from PyPI
pip install flakeradar==1.1.0

# Test the Python API
python -c "from flakeradar import FlakeRadar; print('✅ FlakeRadar v1.1.0 API working!')"

# Test the CLI
flakeradar --help
```

## 📋 What's Being Published

FlakeRadar v1.1.0 includes:
- ✅ Complete Python API implementation
- ✅ Backward compatible CLI
- ✅ All existing features + new API
- ✅ Comprehensive documentation
- ✅ Production-ready code

## 🚀 Ready to Publish!

The package is built and ready. Just need authentication setup:
- `dist/flakeradar-1.1.0-py3-none-any.whl` (57.2 KB)
- `dist/flakeradar-1.1.0.tar.gz` (40.7 KB)

Both files passed integrity checks and are ready for PyPI!
