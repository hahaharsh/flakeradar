# FlakeRadar Local Development Setup

## 🎯 **Quick Start**

### **1. Start Development Server**
```bash
# Install dependencies
pip install -e .

# Start local development server
python dev_server.py
```

### **2. Test Team Features**
```bash
# Set development token
export FLAKERADAR_TOKEN="flake_tk_local_dev_demo_token123"

# Run FlakeRadar with team features
flakeradar --project "MyApp" --environment "local" --results "src/flakeradar/sample_results/*.xml"
```

### **3. Access Dashboard**
- **Team Dashboard**: http://localhost:8000/dashboard/local-dev-team
- **API Health Check**: http://localhost:8000/health
- **Landing Page**: http://localhost:8000

## 🏗️ **What's Working**

### ✅ **Core Features**
- ✅ Local test analysis and flakiness detection
- ✅ AI-powered root cause clustering  
- ✅ HTML report generation
- ✅ Team token validation
- ✅ Team mode activation
- ✅ Jenkins environment detection
- ✅ Local SQLite database for team data

### ✅ **Team Features**
- ✅ Team collaboration mode
- ✅ Central dashboard (basic)
- ✅ Real-time team activity tracking
- ✅ Environment-based analysis
- ✅ Team metrics and statistics

### 🔄 **In Development**
- 🔄 Team result submission (endpoint needs implementation)
- 🔄 Cross-environment analysis (endpoint needs implementation)
- 🔄 Team insights API (endpoint needs implementation)
- 🔄 Advanced dashboard features

## 🛠️ **Development Environment**

### **Local Database**
- **Location**: `~/.flakeradar/local_team_db.sqlite3`
- **Tables**: teams, test_executions, dashboard_metrics
- **Demo Data**: Pre-loaded with demo team and token

### **Development Server**
- **Port**: 8000 (avoiding macOS AirPlay on 5000)
- **Mode**: Flask development server with auto-reload
- **API Base**: http://localhost:8000/api/v1

### **Environment Variables**
```bash
# Required for team features
export FLAKERADAR_TOKEN="flake_tk_local_dev_demo_token123"

# Optional: Backend URL override
export FLAKERADAR_BACKEND_URL="http://localhost:8000"

# Optional: AI features
export OPENAI_API_KEY="your-openai-key"
```

## 📊 **Sample Output**

```bash
✅ FlakeRadar Team mode activated
🔍 Fetching team insights...

🔍 Root Cause Clustering Analysis:
  🟠 database_connectivity: 5 failures, 4 tests affected
     💡 🗄️ Database: Check connection pool settings

📊 Test Analysis Results:
| Test                           | Pass | Fail | Total | Trans | Rate | Flaky? |
|--------------------------------|------|------|-------|-------|------|--------|
| EarnFlowTest#cancelPastOrders  |   0  |   2  |   2   |   0   | 100% | NO     |

🏢 Team Insights:
  • Team dashboard: http://localhost:8000/dashboard/local-dev-team
  • Active environment: local
  • Analysis mode: Team collaboration enabled
```

## 🚀 **Next Steps for Production**

### **Repository Strategy**
1. **Keep current repo private** for enterprise features
2. **Create public community edition** without team features
3. **Deploy backend** to Railway/Render/Vercel
4. **Set up domain** and SSL certificates

### **Backend Deployment**
```bash
# Example Railway deployment
railway login
railway init
railway deploy

# Set environment variables
railway variables set DATABASE_URL=postgresql://...
railway variables set REDIS_URL=redis://...
```

### **Community vs Enterprise Split**
- **Community** (Public): Local analysis, HTML reports, basic CLI
- **Enterprise** (Private): Team collaboration, central dashboard, CI integration

## 🔧 **Troubleshooting**

### **Port 5000 In Use**
- macOS AirPlay uses port 5000
- Development server automatically uses port 8000
- Update `FLAKERADAR_BACKEND_URL` if needed

### **Token Validation Fails**
- Ensure development server is running on port 8000
- Check token format: must start with `flake_tk_`
- Verify `FLAKERADAR_TOKEN` environment variable

### **Import Errors**
- Run `pip install -e .` to install in development mode
- Ensure you're in the virtual environment
- Check Flask installation: `pip install flask>=3.0`

---

**🎯 Ready for local development and team feature testing!**
