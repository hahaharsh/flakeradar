# FlakeRadar Python API - Complete Parameter Guide

## 🎛️ **analyze() Method Parameters**

The `analyze()` method is the core of FlakeRadar's Python API. Here are all the parameters you can configure:

### **Complete Method Signature**
```python
analysis = radar.analyze(
    confidence_threshold=0.7,      # float: 0.0-1.0
    enable_ai=None,                # bool or None
    track_time_to_fix=True,        # bool
    limit_runs=50,                 # int
    max_ai_analysis=20             # int
)
```

## 📊 **Parameter Details**

### 1. **confidence_threshold** (float, default: 0.7)
**Purpose**: Minimum statistical confidence score for classifying a test as flaky
**Range**: 0.0 to 1.0 (0% to 100% confidence)
**Impact**: Higher values = fewer false positives, lower values = catch more potentially flaky tests

```python
# Conservative: Only very confident flaky tests
analysis = radar.analyze(confidence_threshold=0.9)

# Balanced: Good mix of precision and recall
analysis = radar.analyze(confidence_threshold=0.7)  # Default

# Sensitive: Catch potentially flaky tests early
analysis = radar.analyze(confidence_threshold=0.5)
```

**Use Cases**:
- **0.9+**: Production environments where false positives are costly
- **0.7**: General use, good balance
- **0.5**: Early detection, development environments

### 2. **enable_ai** (bool or None, default: None)
**Purpose**: Enable AI-powered failure analysis using OpenAI
**Behavior**: 
- `None` (default): Auto-detect based on `OPENAI_API_KEY` environment variable
- `True`: Force enable (requires API key)
- `False`: Force disable (faster analysis)

```python
# Auto-detect AI availability
analysis = radar.analyze(enable_ai=None)  # Default

# Force enable AI analysis
analysis = radar.analyze(enable_ai=True)

# Disable AI for faster processing
analysis = radar.analyze(enable_ai=False)
```

**Use Cases**:
- **None**: Let FlakeRadar decide based on environment
- **True**: When you want detailed AI insights regardless of performance
- **False**: CI/CD pipelines where speed matters more than AI insights

### 3. **track_time_to_fix** (bool, default: True)
**Purpose**: Track how long tests have been flaky (time-to-fix analytics)
**Impact**: Enables identification of "worst offender" tests that stay flaky longest

```python
# Enable time tracking (recommended)
analysis = radar.analyze(track_time_to_fix=True)  # Default

# Disable for faster analysis
analysis = radar.analyze(track_time_to_fix=False)
```

**Use Cases**:
- **True**: Production monitoring, team accountability
- **False**: One-off analysis, performance-critical scenarios

### 4. **limit_runs** (int, default: 50)
**Purpose**: Number of recent test runs to include in historical analysis
**Impact**: More runs = better statistical confidence, but slower processing

```python
# Quick analysis (fewer runs)
analysis = radar.analyze(limit_runs=20)

# Standard analysis
analysis = radar.analyze(limit_runs=50)  # Default

# Deep historical analysis
analysis = radar.analyze(limit_runs=100)
```

**Use Cases**:
- **20-30**: Quick feedback in development
- **50**: Standard production analysis
- **100+**: Deep investigation of persistent issues

### 5. **max_ai_analysis** (int, default: 20)
**Purpose**: Maximum number of failing tests to analyze with AI
**Impact**: Higher values = more AI insights but slower and more expensive

```python
# Minimal AI analysis
analysis = radar.analyze(max_ai_analysis=5)

# Standard AI analysis
analysis = radar.analyze(max_ai_analysis=20)  # Default

# Comprehensive AI analysis
analysis = radar.analyze(max_ai_analysis=50)
```

**Use Cases**:
- **5-10**: Cost-conscious analysis
- **20**: Good balance of insights and cost
- **50+**: Comprehensive failure analysis

## 🎯 **Common Configuration Patterns**

### **Development Environment**
```python
# Fast feedback for developers
analysis = radar.analyze(
    confidence_threshold=0.6,     # Catch issues early
    enable_ai=False,              # Speed over insights
    track_time_to_fix=False,      # Not needed in dev
    limit_runs=20,                # Quick analysis
    max_ai_analysis=5             # Minimal AI cost
)
```

### **CI/CD Pipeline**
```python
# Balanced for automation
analysis = radar.analyze(
    confidence_threshold=0.7,     # Balanced accuracy
    enable_ai=True,               # Useful insights
    track_time_to_fix=True,       # Track technical debt
    limit_runs=50,                # Good historical context
    max_ai_analysis=15            # Controlled AI cost
)
```

### **Production Monitoring**
```python
# Comprehensive analysis
analysis = radar.analyze(
    confidence_threshold=0.8,     # High confidence
    enable_ai=True,               # Full insights
    track_time_to_fix=True,       # Essential for monitoring
    limit_runs=100,               # Deep historical analysis
    max_ai_analysis=30            # Comprehensive AI analysis
)
```

### **Cost-Conscious Analysis**
```python
# Minimize AI costs
analysis = radar.analyze(
    confidence_threshold=0.7,     # Standard accuracy
    enable_ai=False,              # No AI costs
    track_time_to_fix=True,       # Still track trends
    limit_runs=50,                # Standard analysis
    max_ai_analysis=0             # No AI analysis
)
```

### **Deep Investigation**
```python
# Maximum insights for problem solving
analysis = radar.analyze(
    confidence_threshold=0.5,     # Catch everything
    enable_ai=True,               # Full AI power
    track_time_to_fix=True,       # Complete timeline
    limit_runs=200,               # Maximum history
    max_ai_analysis=100           # Analyze all failures
)
```

## 📈 **Parameter Impact on Results**

### **Analysis Speed**
- **Fastest**: `enable_ai=False`, `limit_runs=20`, `max_ai_analysis=0`
- **Balanced**: Default parameters
- **Slowest**: `enable_ai=True`, `limit_runs=200`, `max_ai_analysis=100`

### **AI Costs (OpenAI API)**
- **Free**: `enable_ai=False`
- **Low**: `max_ai_analysis=5-10`
- **Medium**: `max_ai_analysis=20` (default)
- **High**: `max_ai_analysis=50+`

### **Detection Sensitivity**
- **Conservative**: `confidence_threshold=0.9`
- **Balanced**: `confidence_threshold=0.7` (default)
- **Sensitive**: `confidence_threshold=0.5`

## 🔧 **Dynamic Configuration**

You can also adjust parameters based on context:

```python
import os

# Adjust based on environment
is_production = os.getenv("ENV") == "production"
has_ai_budget = os.getenv("AI_ANALYSIS_BUDGET", "false").lower() == "true"

analysis = radar.analyze(
    confidence_threshold=0.8 if is_production else 0.6,
    enable_ai=has_ai_budget,
    track_time_to_fix=is_production,
    limit_runs=100 if is_production else 30,
    max_ai_analysis=30 if has_ai_budget else 10
)
```

## 📊 **Understanding Results**

The `analyze()` method returns a dictionary with these key metrics:
- `total_tests`: Total number of tests analyzed
- `flaky_tests`: Number of tests classified as flaky
- `high_confidence_flaky`: Tests above your confidence threshold
- `ai_analyzed_count`: Number of tests processed by AI
- `confidence_threshold`: The threshold you specified

This comprehensive parameter system gives you fine-grained control over FlakeRadar's analysis behavior! 🎛️
