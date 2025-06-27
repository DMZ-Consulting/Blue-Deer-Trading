#!/usr/bin/env python3
"""
Specialized Trade Analysis Agent for Team Coordinator Mode

This agent is designed to work in a team with:
1. Database Agent - provides trade data
2. Polygon Agent - provides market data  
3. Analysis Agent (this one) - performs comprehensive analysis

The agent receives structured data and focuses purely on analysis and insights.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
class TradePerformanceMetrics(BaseModel):
    """Comprehensive trade performance metrics"""
    total_return_pct: float
    total_return_dollars: float
    holding_period_days: int
    annualized_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    win_loss_classification: str
    risk_reward_ratio: Optional[float] = None

class MarketConditionsAssessment(BaseModel):
    """Assessment of market conditions during trade"""
    volatility_regime: str
    market_trend: str
    liquidity_assessment: str
    market_stress_level: str
    favorable_conditions: bool
    condition_impact_score: int

class TradeAnalysisReport(BaseModel):
    """Comprehensive trade analysis report"""
    executive_summary: str
    performance_score: int
    strategy_type: str
    performance_metrics: TradePerformanceMetrics
    market_conditions: MarketConditionsAssessment
    execution_quality: str
    risk_management_grade: str
    key_strengths: List[str]
    key_weaknesses: List[str]
    actionable_recommendations: List[str]
    future_considerations: List[str]
    confidence_level: int
    analysis_limitations: Optional[List[str]] = None

def create_trade_analysis_specialist() -> Agent:
    """
    Create a specialized trade analysis agent for team coordinator mode
    
    This agent:
    - Receives trade and market data from other team members
    - Performs comprehensive quantitative and qualitative analysis
    - Provides structured, actionable insights
    - Works efficiently in team coordination workflows
    """
    
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    return Agent(
        name="Trade Analysis Specialist",
        role="Comprehensive Trade Performance Analysis Expert",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools()],
        description="""
        You are an expert trade analyst who synthesizes trade execution data with market conditions 
        to provide comprehensive, actionable performance assessments. You excel at identifying 
        strategy patterns, evaluating execution quality, and providing optimization recommendations.
        """,
        instructions=[
            "🎯 CORE MISSION: Analyze trade performance using provided trade and market data",
            "",
            "📊 DATA ANALYSIS WORKFLOW:",
            "1. RECEIVE DATA: Wait for trade details and market data from team members",
            "2. VALIDATE: Ensure data completeness before proceeding with analysis", 
            "3. CLASSIFY: Identify the trading strategy and objectives",
            "4. QUANTIFY: Calculate comprehensive performance metrics",
            "5. CONTEXTUALIZE: Assess performance relative to market conditions",
            "6. SYNTHESIZE: Generate insights and recommendations",
            "",
            "🔍 ANALYSIS COMPONENTS:",
            "• Performance Calculation: Returns, risk metrics, efficiency ratios",
            "• Strategy Classification: Directional, volatility, income, arbitrage, etc.",
            "• Execution Assessment: Entry/exit timing relative to optimal conditions",
            "• Risk Evaluation: Position sizing, downside protection, exposure management",
            "• Market Context: How environmental factors influenced outcomes",
            "• Benchmark Comparison: Performance vs relevant benchmarks",
            "• ALWAYS Attempt to use QUANTITATIVE analysis to support analyses.",
            "• For all setions of the analysis, provide metrics that support the analysis.",
            "",
            "📈 QUANTITATIVE FOCUS AREAS:",
            "• Total return (% and $), holding period, annualized returns",
            "• Risk-adjusted metrics: Sharpe ratio, Sortino ratio, max drawdown",
            "• Execution efficiency: Slippage, timing quality, fill quality",
            "• Risk metrics: VaR, volatility, correlation, beta",
            "• Opportunity cost: What was given up for this trade",
            "",
            "🌍 MARKET CONDITIONS ASSESSMENT:",
            "• Volatility regime during trade period",
            "• Underlying trend and momentum",
            "• Liquidity conditions and spreads",
            "• Market stress indicators (VIX, credit spreads, etc.)",
            "• Sector/industry specific factors",
            "",
            "💡 INSIGHT GENERATION:",
            "• Distinguish between skill-based and luck-based outcomes",
            "• Identify replicable success factors",
            "• Highlight process improvements opportunities",
            "• Suggest position sizing optimizations",
            "• Recommend timing/execution enhancements",
            "",
            "🎪 OUTPUT STRUCTURE:",
            "• Lead with executive summary and performance score",
            "• Provide detailed quantitative metrics",
            "• Assess market conditions impact",
            "• Grade execution and risk management",
            "• List actionable recommendations",
            "• Include confidence levels and limitations",
            "",
            "🔧 TEAM COORDINATION PROTOCOLS:",
            "• Request missing data rather than making assumptions",
            "• Clearly communicate analysis confidence levels",
            "• Provide structured output for easy integration",
            "• Flag when additional context would improve analysis",
            "• Be ready to incorporate supplementary data sources",
            "",
            "🚨 QUALITY STANDARDS:",
            "• Base all conclusions on quantitative evidence",
            "• Account for transaction costs and realistic execution",
            "• Consider statistical significance of patterns",
            "• Provide balanced assessment (not just positive/negative)",
            "• Quantify uncertainty and confidence levels",
            "• Focus on actionable insights over academic metrics",
            "• Be extremely detailed in your analysis.",
            "• Inidicate where you could use more data to improve your analysis. Include what data you would need."
        ],
        response_model=TradeAnalysisReport,
        structured_outputs=True,
        add_datetime_to_instructions=True,
        markdown=True,
        debug_mode=debug_mode,
    )

def create_trade_analysis_team_member() -> Agent:
    """
    Factory function for creating the analysis specialist as a team member
    
    This version is optimized for working in Team coordinator mode with
    database and polygon agents providing data inputs.
    """
    
    agent = create_trade_analysis_specialist()
    
    # Additional team-specific configurations
    agent.instructions.extend([
        "",
        "🤝 TEAM COLLABORATION SPECIFICS:",
        "• Database Agent will provide: Trade ID, entry/exit data, P&L, position details",
        "• Polygon Agent will provide: Historical prices, volume, volatility, market data",
        "• You analyze: Synthesize all data into comprehensive performance assessment",
        "",
        "📋 COORDINATION WORKFLOW:",
        "1. Wait for database agent to provide complete trade details",
        "2. Wait for polygon agent to provide relevant market data",
        "3. Validate that you have sufficient data for analysis",
        "4. Perform comprehensive analysis using provided data",
        "5. Return structured TradeAnalysisReport with findings",
        "",
        "⚡ EFFICIENCY GUIDELINES:",
        "• Don't duplicate data retrieval - focus on analysis",
        "• Request specific additional data if needed for complete analysis",
        "• Provide preliminary assessment if waiting for more data",
        "• Structure output for easy coordinator processing"
        ""
    ])
    
    return agent

# Test function for development
if __name__ == "__main__":
    from agno.utils.pprint import pprint_run_response
    
    # Create the analysis specialist
    analyst = create_trade_analysis_specialist()
    
    # Example test with mock data
    test_prompt = """
    Analyze this trade:
    
    TRADE DATA:
    - Trade ID: GNUMT0M0
    - Symbol: NVDA
    - Strategy: Call Option Purchase
    - Entry: 2024-05-06 at $1.25 per contract
    - Exit: 2024-05-13 at $2.50 per contract  
    - Position Size: 10 contracts
    - Total P&L: +$1,250 (+100%)
    
    MARKET DATA:
    - NVDA moved from $900 to $950 during period (+5.6%)
    - Implied volatility decreased from 35% to 28%
    - Market trend: Strong bullish momentum
    - Volume: Above average during period
    - VIX: Declined from 18 to 15 (low stress environment)
    
    Provide comprehensive analysis.
    """
    
    print("🧪 Testing Trade Analysis Specialist")
    print("=" * 60)
    
    response = analyst.run(test_prompt)
    pprint_run_response(response, markdown=True) 