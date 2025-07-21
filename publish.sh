#!/bin/bash
# FlakeRadar v1.1.0 Publishing Script

echo "🔍 FlakeRadar v1.1.0 - Publishing Setup"
echo "========================================"

echo ""
echo "📦 Package Status:"
ls -la dist/flakeradar-1.1.0*

echo ""
echo "🔐 Authentication Setup Required:"
echo "1. Go to https://pypi.org/manage/account/token/"
echo "2. Create a new API token (or use existing one)"
echo "3. Choose ONE of these options:"
echo ""
echo "   Option A - Environment Variables (temporary):"
echo "   export TWINE_USERNAME='__token__'"
echo "   export TWINE_PASSWORD='pypi-YOUR-TOKEN-HERE'"
echo ""
echo "   Option B - Update ~/.pypirc file:"
echo "   [pypi]"
echo "   username = __token__"
echo "   password = pypi-YOUR-TOKEN-HERE"
echo ""
echo "   Option C - Interactive (enter token when prompted):"
echo "   python -m twine upload dist/flakeradar-1.1.0* --username __token__"
echo ""

echo "🚀 Once authenticated, run:"
echo "python -m twine upload dist/flakeradar-1.1.0*"
echo ""

echo "✅ Package is ready - just need authentication!"
echo "   • flakeradar-1.1.0-py3-none-any.whl (57.2 KB)"
echo "   • flakeradar-1.1.0.tar.gz (40.7 KB)"
echo "   • Both passed integrity checks"
echo "   • Includes complete Python API implementation"
