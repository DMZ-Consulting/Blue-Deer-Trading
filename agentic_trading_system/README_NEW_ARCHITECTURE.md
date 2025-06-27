# Agentic Trading Strategy Research & Analysis System

## NEW ARCHITECTURE: Separated Research and Analysis

This system has been redesigned with clear separation between research and analysis workflows, enabling autonomous operation while maintaining modularity and extensibility.

## 🎯 Architecture Overview

### Key Principles
- **RESEARCH ONLY**: Research workflow operates independently without trade analysis
- **ANALYSIS WITH FEEDBACK**: Analysis workflow automatically requests research when gaps are found
- **AUTONOMOUS OPERATION**: System continuously improves its bucketing capabilities
- **SHARED KNOWLEDGE**: Central knowledge base serves both workflows
- **CLEAR SEPARATION**: No overlap between research and analysis concerns

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RESEARCH      │    │   KNOWLEDGE      │    │    ANALYSIS     │
│   WORKFLOW      │◄──►│     BASE         │◄──►│    WORKFLOW     │
│                 │    │   (Shared)       │    │                 │
│ • Strategy      │    │ • Strategies     │    │ • Trade         │
│   Research      │    │ • Methods        │    │   Bucketing     │
│ • Method        │    │ • Patterns       │    │ • Gap Detection │
│   Discovery     │    │ • SQL Templates  │    │ • Auto Research │
│ • Knowledge     │    │                  │    │   Requests      │
│   Updates       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔬 Research Workflow

### Purpose
- **ON-DEMAND RESEARCH**: Only runs when specifically requested
- **KNOWLEDGE EXPANSION**: Adds new strategies and methods to knowledge base
- **NO TRADE ANALYSIS**: Focuses purely on research activities

### Capabilities
1. **General Research**: Broad topic investigation
2. **Specific Strategy Research**: Deep dive into particular strategies
3. **Analysis Method Research**: Discovery of new analysis techniques
4. **Market Phenomenon Research**: Investigation of market patterns

### Usage Examples

```python
# General strategy research
system.research_strategy(
    research_topic="momentum trading strategies",
    depth="comprehensive"
)

# Specific strategy research
system.research_specific_strategy("VWAP trading strategy")

# Analysis method research
system.research_analysis_method("time-of-day performance analysis")

# Market phenomenon research
system.research_market_phenomenon("post-earnings announcement drift")
```

## 📊 Analysis Workflow

### Purpose
- **AUTONOMOUS TRADE ANALYSIS**: Analyzes user's trading history
- **STRATEGY BUCKETING**: Categorizes trades into known strategies
- **GAP DETECTION**: Identifies trades that can't be bucketed
- **RESEARCH FEEDBACK LOOP**: Automatically requests research for gaps

### Autonomous Feedback Loop

```
1. ANALYZE TRADES
   ├─ Load trade data
   ├─ Apply knowledge base patterns
   └─ Calculate coverage percentage

2. DETECT GAPS
   ├─ Identify unbucketable trades
   ├─ Analyze common patterns
   └─ Generate research requests

3. EXECUTE RESEARCH
   ├─ Research specific patterns
   ├─ Update knowledge base
   └─ Determine if re-analysis needed

4. RE-ANALYZE (if needed)
   └─ Repeat until coverage threshold met
```

### Usage Examples

```python
# Autonomous trade analysis
system.analyze_trades(
    user_id=None,        # All users
    days=90,             # Last 90 days
    min_coverage=0.75    # 75% coverage target
)

# Specific user analysis
system.analyze_trades(
    user_id="user123",
    days=30,
    min_coverage=0.80
)
```

## 🏗️ System Architecture

### Directory Structure

```
agentic_trading_system/
├── agents/                    # Individual agent definitions
│   ├── strategy_researcher.py    # Research strategies
│   ├── analysis_method_developer.py  # Develop analysis methods
│   ├── knowledge_updater.py     # Update knowledge base
│   └── postgres_agent.py        # Database interactions
├── teams/                     # Team coordinations
│   ├── research_team.py         # Research coordination
│   └── analysis_team.py         # Analysis coordination
├── workflows/                 # Main workflows
│   ├── research_only.py         # Research-only workflow
│   ├── trade_analysis.py        # Analysis with feedback loop
│   └── strategy_discovery.py    # Legacy combined workflow
├── utils/                     # Utilities and helpers
│   ├── knowledge_manager.py     # Knowledge base management
│   └── initialize_documents.py  # Document initialization
├── data/                      # Knowledge base content
│   └── knowledge/              # Base knowledge documents
├── tests/                     # Test suites
│   └── test_separated_workflows.py  # Architecture tests
└── run.py                     # Main system entry point
```

### Key Classes

#### `AgenticTradingSystem`
- **Main orchestrator** with separated workflows
- **New methods**:
  - `research_strategy()`: Pure research
  - `analyze_trades()`: Autonomous analysis  
  - `research_specific_strategy()`: Targeted research
  - `research_analysis_method()`: Method research
- **Legacy compatibility**: `discover_strategies()` still available

#### `ResearchOnlyWorkflow`
- **Pure research** without trade analysis
- **Structured findings** with credibility scoring
- **Knowledge base integration** with organized updates

#### `TradeAnalysisWorkflow`
- **Autonomous analysis** with research feedback loop
- **Gap detection** for unbucketable trades
- **Research requests** based on trade patterns
- **Coverage monitoring** with configurable thresholds

## 🚀 Getting Started

### 1. Initialize System

```python
from run import system

# System auto-initializes with:
# - Shared knowledge base
# - Research workflow  
# - Analysis workflow
# - Legacy compatibility
```

### 2. Pure Research Session

```python
# Research momentum strategies
results = system.research_strategy(
    research_topic="momentum trading strategies and breakout patterns",
    depth="comprehensive"
)

for response in results:
    print(response.content)
```

### 3. Autonomous Trade Analysis

```python
# Analyze trades with automatic research
results = system.analyze_trades(
    user_id=None,       # All users
    days=90,            # Last 90 days  
    min_coverage=0.75   # 75% target coverage
)

for response in results:
    print(response.content)
```

### 4. Run Examples

```bash
# Run all system examples
python run.py examples

# Test the new architecture
python tests/test_separated_workflows.py

# Test specific components
python tests/test_separated_workflows.py research
python tests/test_separated_workflows.py analysis
```

## 🔧 Configuration

### Environment Variables

```bash
# Enable debug mode for detailed agent interactions
DEBUG_MODE=true

# OpenAI API key for agents
OPENAI_API_KEY=your_openai_key

# Database connection
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Knowledge Base Configuration

The system uses a shared `DocumentKnowledgeBase` with:
- **LanceDB** vector storage for fast similarity search
- **OpenAI embeddings** for semantic understanding
- **Hybrid search** combining vector and keyword search
- **Automatic persistence** with incremental updates

## 📈 Benefits of New Architecture

### 1. Clear Separation of Concerns
- **Research** focuses purely on knowledge discovery
- **Analysis** focuses purely on trade categorization
- **No overlap** or confusion between responsibilities

### 2. Autonomous Operation
- **Automatic gap detection** identifies missing knowledge
- **Targeted research requests** fill specific gaps
- **Continuous improvement** without manual intervention

### 3. Scalability and Modularity
- **Independent workflows** can be scaled separately
- **Modular agents** can be reused across workflows
- **Factory patterns** enable easy extension

### 4. Improved User Experience
- **Focused operations** with clear purposes
- **Predictable behavior** with well-defined inputs/outputs
- **Progress tracking** through workflow events

## 🧪 Testing

### Automated Tests

```bash
# Run all architecture tests
python tests/test_separated_workflows.py

# Test specific components
python tests/test_separated_workflows.py separation
python tests/test_separated_workflows.py knowledge
python tests/test_separated_workflows.py agents
```

### Manual Testing

```bash
# Test research workflow only
python tests/test_separated_workflows.py research

# Test analysis workflow (requires database)
python tests/test_separated_workflows.py analysis
```

## 🔮 Future Enhancements

### 1. Enhanced Research Capabilities
- **Academic paper integration** with PDF parsing
- **Real-time market data** for research validation
- **Community knowledge** sharing and updates

### 2. Advanced Analysis Features
- **Multi-timeframe analysis** across different periods
- **Cross-asset analysis** for portfolio-level insights
- **Performance prediction** based on historical patterns

### 3. Integration Improvements
- **Real-time analysis** for live trading
- **Alert systems** for new pattern detection
- **API endpoints** for external system integration

## 📞 Support

For questions about the new architecture:

1. **Check documentation**: Review this README and code comments
2. **Run tests**: Use the test suite to verify functionality
3. **Review examples**: Check the example usage in `run.py`
4. **Examine workflows**: Study the workflow implementations

---

## Migration from Old System

### What Changed
- **Split monolithic workflow** into research and analysis
- **Added autonomous feedback loop** for gap detection
- **Improved knowledge base management** with structured updates
- **Enhanced modularity** with clear component separation

### Compatibility
- **Legacy methods preserved**: `discover_strategies()` still works
- **Same agent/team factories**: Existing factory patterns maintained
- **Same knowledge base**: No changes to knowledge storage format
- **Same configuration**: Environment variables and setup unchanged

### Recommended Migration
1. **Update calls** to use new methods (`research_strategy`, `analyze_trades`)
2. **Test new workflows** with existing data
3. **Gradually transition** from legacy to new architecture
4. **Monitor performance** and adjust coverage thresholds

The new architecture provides a more robust, autonomous, and maintainable system for trading strategy research and analysis while preserving all existing functionality. 