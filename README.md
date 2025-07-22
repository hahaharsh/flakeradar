<div align="center">

# 🔍 FlakeRadar

### **AI-Powered Test Flakiness Detection & Team Collaboration**

<p>
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Enterprise-Ready-green.svg" alt="Enterprise Ready">
</p>

Transform raw test results into actionable insights with **statistical confidence scoring**, **AI-powered root cause analysis**, and **team collaboration features**.

</div>

---

## 🚀 **Quick Start**

```bash
# Install and analyze
pip install flakeradar
flakeradar --project "MyApp" --results "test-results/*.xml"
open flakeradar_report.html
```

**Python API:**
```python
from flakeradar import FlakeRadar

with FlakeRadar(project="MyApp") as radar:
    radar.add_results("test-results/*.xml")
    analysis = radar.analyze(confidence_threshold=0.7, enable_ai=True)
    radar.generate_html_report("report.html")
```

---

## 🎯 **Key Features**

### **🔍 Smart Analysis**
- **Statistical Confidence Scoring** - Wilson intervals eliminate false positives
- **AI Root Cause Clustering** - Groups failures by actual causes
- **Time-to-Fix Tracking** - Identifies chronic flaky tests

### **👥 Team Collaboration** 
- **Central Dashboard** - Shared analytics across environments
- **Multi-Environment Tracking** - Dev → Staging → Production insights
- **CI/CD Integration** - Jenkins, GitHub Actions, REST API

### **📊 Enterprise Ready**
- **Production-Tested Accuracy** - Fixed confidence calculations
- **Secure Token Authentication** - Team collaboration with proper security
- **Scalable Architecture** - Supports teams of any size

---

## 🔧 **Team Setup**

### **1. Start Team Dashboard**
```bash
python -m flakeradar.dev_server
# Dashboard: http://localhost:8000/dashboard/your-team-id
```

### **2. Create Team Token**
```bash
curl -X POST http://localhost:8000/api/v1/team/tokens \
  -d '{"team_name": "YourTeam", "environment": "production"}'
```

### **3. Jenkins Integration**
```groovy
environment {
    FLAKERADAR_TEAM_TOKEN = credentials('flakeradar-team-token')
}
post {
    always {
        sh '''
            pip install flakeradar
            flakeradar --project "${JOB_NAME}" \
                      --results "test-results/*.xml" \
                      --team-token "${FLAKERADAR_TEAM_TOKEN}" \
                      --environment "${ENV}"
        '''
    }
}
```

### **4. GitHub Actions**
```yaml
- name: FlakeRadar Analysis
  env:
    FLAKERADAR_TEAM_TOKEN: ${{ secrets.FLAKERADAR_TEAM_TOKEN }}
  run: |
    pip install flakeradar
    flakeradar --project "${{ github.repository }}" \
              --results "test-results/*.xml" \
              --team-token "$FLAKERADAR_TEAM_TOKEN" \
              --environment "ci"
```

---

## 📖 **CLI Reference**

```bash
flakeradar [OPTIONS]

# Core Parameters
--project TEXT              Project name (required)
--results TEXT              Test files pattern (required, e.g., "*.xml")

# Team Collaboration
--team-token TEXT           Team token (flake_tk_...)
--dashboard-url TEXT        Dashboard URL
--environment TEXT          Environment (dev/staging/prod)

# Analysis Options  
--confidence-threshold FLOAT  Statistical threshold (0.0-1.0, default: 0.7)
--enable-ai / --no-ai        AI analysis (auto-detects API key)
--output TEXT               Report filename (default: flakeradar_report.html)
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

**❌ "Invalid token" error**
```bash
# Verify token format
echo $FLAKERADAR_TEAM_TOKEN  # Should start with "flake_tk_"

# Test token
curl -X POST "$DASHBOARD_URL/api/v1/team/validate" \
  -H "Authorization: Bearer $FLAKERADAR_TEAM_TOKEN"
```

**❌ Dashboard shows no data**
```bash
# Check Jenkins console output for submission errors
# Verify environment variables are set correctly
```

**❌ Analysis too slow**
```bash
# Optimize for large test suites
flakeradar --limit-runs 20 --max-ai-analysis 5 --confidence-threshold 0.8
```

---

## 📊 **Sample Output**

```bash
🚨 Flaky Test Analysis Results:
  📊 Total Tests: 245 | Flaky: 12 | High Confidence: 8
  
🔴 High Priority Flaky Tests:
  DatabaseTest#connectionPool (82% confidence, 14 days flaky)
  AuthTest#tokenRefresh (76% confidence, 7 days flaky)

🔍 Root Cause Analysis:
  🗄️ Database connectivity: 8 tests affected
  ⏱️ Timing issues: 4 tests affected
  
🤖 AI Insights: 12 tests analyzed
✅ Report generated: flakeradar_report.html
```

---

## 🏢 **Enterprise Features**

- **Mathematical Rigor** - Wilson Score confidence intervals
- **Production Accuracy** - Fixed edge cases for 0%/100% failure rates  
- **Team Analytics** - Cross-environment insights and contributor tracking
- **Security** - Token-based authentication with rotation support
- **Integration** - Jenkins, GitHub Actions, REST API, Python API
- **Scalability** - Supports individual developers to enterprise teams

---

## 📚 **Links**

- **[GitHub Repository](https://github.com/hahaharsh/flakeradar)** - Source code and issues
- **[Documentation](https://github.com/hahaharsh/flakeradar/wiki)** - Detailed guides
- **[Support](https://github.com/hahaharsh/flakeradar/issues)** - Questions and bug reports

---

<div align="center">

**Ready to eliminate flaky tests?**

[🚀 Get Started](https://github.com/hahaharsh/flakeradar) | [📖 Documentation](https://github.com/hahaharsh/flakeradar/wiki) | [💬 Support](https://github.com/hahaharsh/flakeradar/issues)

*Built by engineers who understand the pain of flaky tests*

</div>
