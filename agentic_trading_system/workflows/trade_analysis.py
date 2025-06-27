"""
Trade Analysis Workflow - Autonomous Trading Strategy Detection & Research System

This workflow implements a clear separation between research and analysis:

1. ANALYSIS PHASE: Analyzes user's trade history using existing knowledge base
   - Buckets trades into known strategies
   - Identifies unbucketable trades
   - Calculates confidence scores

2. RESEARCH PHASE: Only triggered when gaps are identified
   - Researches specific patterns found in unbucketable trades
   - Updates knowledge base with new findings
   - Re-runs analysis with enhanced knowledge

3. FEEDBACK LOOP: Autonomous detection and research of gaps
   - Monitors for trades that can't be categorized
   - Automatically requests targeted research
   - Continuously improves bucketing capabilities

Architecture:
- TradeAnalysisWorkflow: Main orchestrator for trade analysis
- StrategyBucketingAgent: Buckets trades using knowledge base
- GapDetectionAgent: Identifies research needs from unbucketable trades
- ResearchCoordinator: Manages research requests and knowledge updates
"""

import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator, Tuple
from textwrap import dedent

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.team import Team
from agno.workflow import Workflow, RunResponse, RunEvent
from agno.knowledge.document import DocumentKnowledgeBase
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.duckduckgo import DuckDuckGoTools


# ===== DATA MODELS =====

class TradeStrategy(BaseModel):
    """Identified trading strategy for a trade"""
    strategy_name: str = Field(..., description="Name of the identified strategy")
    strategy_type: str = Field(..., description="Category (momentum, mean_reversion, etc.)")
    confidence_score: float = Field(..., description="Confidence in this classification (0-1)")
    key_indicators: List[str] = Field(..., description="Indicators that led to this classification")
    timeframe: str = Field(..., description="Timeframe category (scalp, intraday, swing, etc.)")
    reasoning: str = Field(..., description="Explanation of why this trade fits this strategy")

class TradeBucket(BaseModel):
    """A bucket of trades categorized by strategy"""
    strategy: TradeStrategy
    trade_ids: List[str] = Field(..., description="List of trade IDs in this bucket")
    trade_count: int = Field(..., description="Number of trades in bucket")
    performance_summary: str = Field(..., description="Performance summary for this bucket")
    patterns: List[str] = Field(..., description="Common patterns observed in these trades")

class UnbucketableTrade(BaseModel):
    """Trade that couldn't be categorized"""
    trade_id: str
    reason: str = Field(..., description="Why this trade couldn't be bucketed")
    observed_patterns: List[str] = Field(..., description="Patterns observed but not matching known strategies")
    research_suggestions: List[str] = Field(..., description="Suggested research areas to understand this trade")

class TradeAnalysisResult(BaseModel):
    """Complete analysis results"""
    total_trades: int
    bucketed_trades: List[TradeBucket]
    unbucketable_trades: List[UnbucketableTrade]
    coverage_percentage: float = Field(..., description="Percentage of trades successfully bucketed")
    analysis_timestamp: str
    knowledge_gaps: List[str] = Field(..., description="Identified knowledge gaps requiring research")

class ResearchRequest(BaseModel):
    """Request for targeted research"""
    research_focus: str = Field(..., description="Specific area to research")
    unbucketable_patterns: List[str] = Field(..., description="Patterns that triggered this request")
    trade_characteristics: Dict[str, Any] = Field(..., description="Characteristics of unbucketable trades")
    priority: str = Field(..., description="Priority level (high, medium, low)")

class ResearchResult(BaseModel):
    """Result from targeted research"""
    research_focus: str
    new_strategies: List[str] = Field(..., description="New strategies discovered")
    new_analysis_methods: List[str] = Field(..., description="New analysis methods to apply")
    knowledge_updates: List[str] = Field(..., description="Updates made to knowledge base")
    should_reanalyze: bool = Field(..., description="Whether to re-run analysis with new knowledge")


# ===== ANALYSIS AGENTS =====

def create_strategy_bucketing_agent(knowledge_base: DocumentKnowledgeBase) -> Agent:
    """Agent that buckets trades into known strategies using knowledge base"""
    knowledge_tools = KnowledgeTools(
        knowledge=knowledge_base,
        search=True,
        analyze=True,
        think=True,
    )
    
    return Agent(
        name="Strategy Bucketing Agent",
        role="Categorize trades into known trading strategies using knowledge base",
        model=OpenAIChat(id="gpt-4o"),
        tools=[knowledge_tools, ReasoningTools()],
        instructions=[
            "You analyze trading data to categorize trades into known strategies.",
            "Search the knowledge base thoroughly for strategy patterns before making classifications.",
            "For each trade, identify the most likely strategy based on:",
            "- Entry/exit timing patterns",
            "- Position sizing relative to account",
            "- Duration and timeframe",
            "- Market conditions and price action",
            "- Risk/reward characteristics",
            "",
            "Assign confidence scores based on how well the trade matches known patterns.",
            "Only classify trades you're confident about (>0.7 confidence).",
            "For uncertain trades, mark them as unbucketable with detailed reasoning.",
            "",
            "Focus on identifying:",
            "- Momentum strategies (trend following, breakouts)",
            "- Mean reversion strategies (support/resistance, oversold bounces)",
            "- Scalping strategies (quick in/out, small profits)",
            "- Swing strategies (multi-day holds)",
            "- Risk management patterns (stop losses, position sizing)",
        ],
        knowledge=knowledge_base,
        search_knowledge=True,
        response_model=List[TradeBucket],
        add_datetime_to_instructions=True,
        markdown=True,
    )

def create_gap_detection_agent() -> Agent:
    """Agent that identifies what research is needed for unbucketable trades"""
    return Agent(
        name="Gap Detection Agent",
        role="Identify research needs from unbucketable trades",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools()],
        instructions=[
            "You analyze unbucketable trades to identify what research is needed.",
            "Look for patterns in trades that couldn't be categorized:",
            "- Similar timing patterns",
            "- Similar symbols or sectors",
            "- Similar position sizes or durations",
            "- Similar market conditions",
            "",
            "Generate specific research requests that would help categorize these trades:",
            "- What strategy type might this represent?",
            "- What market conditions enable this pattern?",
            "- What indicators or signals might drive this approach?",
            "- What risk management approach is being used?",
            "",
            "Prioritize research based on:",
            "- Number of trades affected",
            "- Potential profitability",
            "- Frequency of pattern occurrence",
            "- Strategic importance",
        ],
        response_model=List[ResearchRequest],
        add_datetime_to_instructions=True,
        markdown=True,
    )


# ===== RESEARCH COORDINATION =====

def create_research_coordinator(knowledge_base: DocumentKnowledgeBase) -> Team:
    """Team that handles research requests and updates knowledge base"""
    
    # Research agent for investigating specific patterns
    research_agent = Agent(
        name="Pattern Research Agent",
        role="Research specific trading patterns and strategies",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools(), ReasoningTools()],
        instructions=[
            "You research specific trading patterns and strategies on demand.",
            "When given unbucketable trade patterns, research:",
            "- Known strategies that match these characteristics",
            "- Academic or industry literature on similar patterns",
            "- Risk management approaches for these trades",
            "- Market conditions that favor these strategies",
            "",
            "Focus on practical, testable insights that can improve trade categorization.",
            "Provide specific criteria for identifying these strategies in future trades.",
            "Include risk characteristics and performance expectations.",
        ],
        add_datetime_to_instructions=True,
        markdown=True,
    )
    
    # Knowledge integration agent
    knowledge_agent = Agent(
        name="Knowledge Integration Agent",
        role="Integrate research findings into knowledge base",
        model=OpenAIChat(id="gpt-4o"),
        tools=[KnowledgeTools(knowledge=knowledge_base, add_few_shot=True), ReasoningTools()],
        instructions=[
            "You integrate new research findings into the knowledge base.",
            "When research identifies new strategies or patterns:",
            "- Create structured strategy definitions",
            "- Define identification criteria and patterns",
            "- Specify risk characteristics and timeframes",
            "- Provide examples and use cases",
            "",
            "Ensure new knowledge integrates well with existing strategies.",
            "Avoid duplication and maintain knowledge base quality.",
            "Focus on actionable insights for trade categorization.",
        ],
        knowledge=knowledge_base,
        add_datetime_to_instructions=True,
        markdown=True,
    )
    
    return Team(
        name="Research Coordinator",
        mode="coordinate",
        model=Claude(id="claude-3-5-sonnet-20241022"),
        members=[research_agent, knowledge_agent],
        tools=[ReasoningTools()],
        instructions=[
            "You coordinate research to fill knowledge gaps in trade analysis.",
            "When given research requests:",
            "1. Have the research agent investigate the specific patterns",
            "2. Have the knowledge agent integrate findings into the knowledge base",
            "3. Determine if re-analysis is needed with the new knowledge",
            "",
            "Focus on filling gaps that will improve trade categorization.",
            "Ensure research is targeted and actionable.",
            "Maintain high knowledge base quality and consistency.",
        ],
        response_model=ResearchResult,
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
    )


# ===== MAIN WORKFLOW =====

class TradeAnalysisWorkflow(Workflow):
    """
    Autonomous trade analysis workflow with research feedback loop.
    
    This workflow:
    1. Analyzes trades using existing knowledge to bucket them into strategies
    2. Identifies trades that can't be bucketed (gaps in knowledge)
    3. Automatically requests research to fill knowledge gaps
    4. Updates knowledge base with research findings
    5. Re-analyzes trades with enhanced knowledge
    """
    
    description: str = dedent("""\
        Autonomous trading strategy detection system that continuously improves
        its ability to categorize trades by researching gaps in knowledge when
        trades cannot be properly bucketed into known strategies.
        """)
    
    def __init__(self, postgres_agent, knowledge_base: DocumentKnowledgeBase):
        super().__init__()
        self.postgres_agent = postgres_agent
        self.knowledge_base = knowledge_base
        self.bucketing_agent = create_strategy_bucketing_agent(knowledge_base)
        self.gap_detector = create_gap_detection_agent()
        self.research_coordinator = create_research_coordinator(knowledge_base)
        
        # Analysis parameters
        self.min_coverage_threshold = 0.75  # Minimum 75% of trades should be bucketable
        self.max_research_iterations = 3    # Maximum research cycles
        
    def run(self, 
            user_id: Optional[str] = None,
            time_period_days: int = 90,
            min_coverage_threshold: Optional[float] = None) -> Iterator[RunResponse]:
        """
        Run complete trade analysis with autonomous research loop.
        
        Args:
            user_id: Specific user to analyze (None for all users)
            time_period_days: How many days back to analyze
            min_coverage_threshold: Minimum % trades that must be bucketable
        """
        
        if min_coverage_threshold:
            self.min_coverage_threshold = min_coverage_threshold
        
        yield RunResponse(
            content=f"🔍 Starting autonomous trade analysis for {time_period_days} days",
            event=RunEvent.workflow_started
        )
        
        # Step 1: Fetch trade data
        yield RunResponse(
            content="📊 Fetching trade data for analysis...",
            event=RunEvent.tool_call_started
        )
        
        trade_data = self._fetch_trade_data(user_id, time_period_days)
        if trade_data.empty:
            yield RunResponse(
                content="❌ No trade data found for analysis",
                event=RunEvent.workflow_completed
            )
            return
        
        yield RunResponse(
            content=f"✅ Loaded {len(trade_data)} trades for analysis",
            event=RunEvent.tool_call_completed
        )
        
        # Step 2: Initial analysis with current knowledge
        analysis_result = None
        research_iteration = 0
        
        while research_iteration <= self.max_research_iterations:
            yield RunResponse(
                content=f"🧠 Running trade analysis (iteration {research_iteration + 1})...",
                event=RunEvent.tool_call_started
            )
            
            analysis_result = self._analyze_trades(trade_data)
            
            yield RunResponse(
                content=f"📈 Analysis complete: {analysis_result.coverage_percentage:.1f}% coverage "
                       f"({len(analysis_result.bucketed_trades)} buckets, "
                       f"{len(analysis_result.unbucketable_trades)} unbucketable)",
                event=RunEvent.tool_call_completed
            )
            
            # Check if coverage is sufficient
            if analysis_result.coverage_percentage >= self.min_coverage_threshold:
                yield RunResponse(
                    content=f"✅ Coverage threshold met ({analysis_result.coverage_percentage:.1f}% >= {self.min_coverage_threshold*100:.1f}%)",
                    event=RunEvent.tool_call_completed
                )
                break
            
            # Check if we have unbucketable trades to research
            if not analysis_result.unbucketable_trades:
                yield RunResponse(
                    content="⚠️ No unbucketable trades found but coverage is low. Manual review needed.",
                    event=RunEvent.tool_call_completed
                )
                break
            
            # Step 3: Detect research gaps
            yield RunResponse(
                content=f"🔬 Detecting research needs for {len(analysis_result.unbucketable_trades)} unbucketable trades...",
                event=RunEvent.tool_call_started
            )
            
            research_requests = self._detect_research_gaps(analysis_result.unbucketable_trades)
            
            if not research_requests:
                yield RunResponse(
                    content="❌ Could not identify specific research needs. Manual analysis required.",
                    event=RunEvent.workflow_completed
                )
                break
            
            yield RunResponse(
                content=f"📝 Identified {len(research_requests)} research requests",
                event=RunEvent.tool_call_completed
            )
            
            # Step 4: Execute research
            yield RunResponse(
                content="🔍 Executing targeted research to fill knowledge gaps...",
                event=RunEvent.tool_call_started
            )
            
            research_results = self._execute_research(research_requests)
            
            if not research_results.should_reanalyze:
                yield RunResponse(
                    content="📚 Research complete but no significant improvements expected",
                    event=RunEvent.tool_call_completed
                )
                break
            
            yield RunResponse(
                content=f"✅ Research complete: {len(research_results.new_strategies)} new strategies, "
                       f"{len(research_results.knowledge_updates)} knowledge updates",
                event=RunEvent.tool_call_completed
            )
            
            research_iteration += 1
        
        # Step 5: Generate final analysis report
        yield RunResponse(
            content="📋 Generating comprehensive analysis report...",
            event=RunEvent.tool_call_started
        )
        
        final_report = self._generate_analysis_report(analysis_result, research_iteration)
        
        yield RunResponse(
            content=final_report,
            event=RunEvent.workflow_completed
        )
    
    def _fetch_trade_data(self, user_id: Optional[str], days: int) -> pd.DataFrame:
        """Fetch trade data for analysis"""
        where_clause = ""
        if user_id:
            where_clause = f"WHERE user_id = '{user_id}' AND"
        else:
            where_clause = "WHERE"
        
        sql_query = f"""
        SELECT 
            trade_id, symbol, side, quantity,
            entry_price, exit_price, entry_time, exit_time,
            pnl, fees, user_id,
            EXTRACT(EPOCH FROM (exit_time - entry_time))/3600 as duration_hours,
            EXTRACT(DOW FROM entry_time) as entry_day_of_week,
            EXTRACT(HOUR FROM entry_time) as entry_hour,
            EXTRACT(MONTH FROM entry_time) as entry_month,
            CASE WHEN pnl > 0 THEN 'WIN' ELSE 'LOSS' END as outcome,
            -- Calculate position size relative to account (simplified)
            quantity * entry_price as position_value
        FROM trades 
        {where_clause} exit_time IS NOT NULL
        AND entry_time >= NOW() - INTERVAL '{days} days'
        ORDER BY entry_time DESC;
        """
        
        try:
            conn = self.postgres_agent.tools[0].connection
            return pd.read_sql_query(sql_query, conn)
        except Exception as e:
            print(f"Error fetching trade data: {e}")
            return pd.DataFrame()
    
    def _analyze_trades(self, trade_data: pd.DataFrame) -> TradeAnalysisResult:
        """Analyze trades and bucket them into strategies"""
        
        # Convert DataFrame to structured format for agent
        trades_json = trade_data.to_json(orient='records', date_format='iso')
        
        # Run bucketing analysis
        prompt = f"""
        Analyze the following {len(trade_data)} trades and categorize them into trading strategies.
        
        For each strategy bucket you identify:
        1. Use the knowledge base to find matching strategy patterns
        2. Group similar trades together
        3. Calculate confidence scores based on pattern matches
        4. Identify key characteristics that define each bucket
        
        Trade Data:
        {trades_json}
        
        Focus on creating meaningful buckets that represent distinct trading approaches.
        Mark trades as unbucketable if they don't clearly fit known strategy patterns.
        """
        
        bucketing_response = self.bucketing_agent.run(prompt)
        
        # Parse bucketed trades
        try:
            if hasattr(bucketing_response, 'content'):
                bucketed_trades = bucketing_response.content
            else:
                bucketed_trades = bucketing_response
                
            if isinstance(bucketed_trades, str):
                import json
                bucketed_trades = json.loads(bucketed_trades)
            
            if not isinstance(bucketed_trades, list):
                bucketed_trades = []
        except:
            bucketed_trades = []
        
        # Calculate coverage and identify unbucketable trades
        bucketed_trade_ids = set()
        for bucket in bucketed_trades:
            if isinstance(bucket, dict) and 'trade_ids' in bucket:
                bucketed_trade_ids.update(bucket['trade_ids'])
        
        unbucketable_trade_ids = set(trade_data['trade_id'].astype(str)) - bucketed_trade_ids
        
        # Create unbucketable trade records
        unbucketable_trades = []
        for trade_id in unbucketable_trade_ids:
            trade_row = trade_data[trade_data['trade_id'].astype(str) == trade_id].iloc[0]
            unbucketable_trades.append(UnbucketableTrade(
                trade_id=trade_id,
                reason="No matching strategy pattern found in knowledge base",
                observed_patterns=[
                    f"Duration: {trade_row.get('duration_hours', 0):.1f} hours",
                    f"Symbol: {trade_row.get('symbol', 'Unknown')}",
                    f"Side: {trade_row.get('side', 'Unknown')}",
                    f"Outcome: {trade_row.get('outcome', 'Unknown')}"
                ],
                research_suggestions=[
                    f"Research {trade_row.get('symbol', 'Unknown')} trading patterns",
                    f"Investigate {trade_row.get('duration_hours', 0):.1f}-hour duration strategies",
                    f"Study {trade_row.get('side', 'Unknown')} entry patterns"
                ]
            ))
        
        coverage_percentage = (len(bucketed_trade_ids) / len(trade_data)) * 100
        
        return TradeAnalysisResult(
            total_trades=len(trade_data),
            bucketed_trades=bucketed_trades,
            unbucketable_trades=unbucketable_trades,
            coverage_percentage=coverage_percentage,
            analysis_timestamp=datetime.now().isoformat(),
            knowledge_gaps=[f"Pattern analysis needed for {len(unbucketable_trades)} trades"]
        )
    
    def _detect_research_gaps(self, unbucketable_trades: List[UnbucketableTrade]) -> List[ResearchRequest]:
        """Detect what research is needed for unbucketable trades"""
        
        prompt = f"""
        Analyze these {len(unbucketable_trades)} unbucketable trades to identify research needs.
        
        Unbucketable Trades:
        {json.dumps([trade.model_dump() for trade in unbucketable_trades], indent=2)}
        
        Look for patterns and generate specific research requests that would help categorize these trades.
        Focus on actionable research that can lead to new strategy definitions.
        """
        
        gap_response = self.gap_detector.run(prompt)
        
        try:
            if hasattr(gap_response, 'content'):
                research_requests = gap_response.content
            else:
                research_requests = gap_response
                
            if isinstance(research_requests, str):
                research_requests = json.loads(research_requests)
            
            if not isinstance(research_requests, list):
                return []
                
            return [ResearchRequest(**req) if isinstance(req, dict) else req for req in research_requests]
        except:
            return []
    
    def _execute_research(self, research_requests: List[ResearchRequest]) -> ResearchResult:
        """Execute research requests and update knowledge base"""
        
        prompt = f"""
        Execute the following research requests to fill knowledge gaps in trade analysis:
        
        Research Requests:
        {json.dumps([req.model_dump() for req in research_requests], indent=2)}
        
        For each request:
        1. Research the specific trading patterns and strategies
        2. Identify concrete criteria for recognizing these patterns
        3. Define new strategy categories if needed
        4. Update the knowledge base with findings
        
        Focus on practical, testable insights that will improve trade categorization.
        """
        
        research_response = self.research_coordinator.run(prompt)
        
        try:
            if hasattr(research_response, 'content'):
                result = research_response.content
            else:
                result = research_response
                
            if isinstance(result, str):
                result = json.loads(result)
            
            return ResearchResult(**result) if isinstance(result, dict) else ResearchResult(
                research_focus="Combined research",
                new_strategies=[],
                new_analysis_methods=[],
                knowledge_updates=["Research executed"],
                should_reanalyze=True
            )
        except:
            return ResearchResult(
                research_focus="Research execution",
                new_strategies=[],
                new_analysis_methods=[],
                knowledge_updates=["Research attempted"],
                should_reanalyze=False
            )
    
    def _generate_analysis_report(self, analysis_result: TradeAnalysisResult, iterations: int) -> str:
        """Generate comprehensive analysis report"""
        
        report = f"""
# 📊 Autonomous Trade Analysis Report

**Analysis Date**: {analysis_result.analysis_timestamp}
**Research Iterations**: {iterations}
**Total Trades Analyzed**: {analysis_result.total_trades}

## 🎯 Coverage Summary

- **Bucketed Trades**: {len(analysis_result.bucketed_trades)} strategy buckets
- **Unbucketable Trades**: {len(analysis_result.unbucketable_trades)} trades
- **Coverage Percentage**: {analysis_result.coverage_percentage:.1f}%
- **Threshold Met**: {'✅ Yes' if analysis_result.coverage_percentage >= self.min_coverage_threshold * 100 else '❌ No'}

## 📈 Strategy Buckets

"""
        
        for i, bucket in enumerate(analysis_result.bucketed_trades, 1):
            if isinstance(bucket, dict):
                strategy_name = bucket.get('strategy', {}).get('strategy_name', f'Strategy {i}')
                trade_count = bucket.get('trade_count', 0)
                confidence = bucket.get('strategy', {}).get('confidence_score', 0)
                
                report += f"""
### {i}. {strategy_name}
- **Trades**: {trade_count}
- **Confidence**: {confidence:.2f}
- **Type**: {bucket.get('strategy', {}).get('strategy_type', 'Unknown')}
"""
        
        if analysis_result.unbucketable_trades:
            report += f"""

## ❓ Unbucketable Trades

{len(analysis_result.unbucketable_trades)} trades could not be categorized:

"""
            for trade in analysis_result.unbucketable_trades[:5]:  # Show first 5
                report += f"- **Trade {trade.trade_id}**: {trade.reason}\n"
            
            if len(analysis_result.unbucketable_trades) > 5:
                report += f"- ... and {len(analysis_result.unbucketable_trades) - 5} more\n"
        
        report += f"""

## 🔍 Knowledge Gaps

"""
        for gap in analysis_result.knowledge_gaps:
            report += f"- {gap}\n"
        
        report += f"""

## 🎯 Recommendations

"""
        
        if analysis_result.coverage_percentage < self.min_coverage_threshold * 100:
            report += "- Additional research needed to improve trade categorization\n"
            report += "- Consider manual review of unbucketable trades\n"
        else:
            report += "- Trade categorization system is performing well\n"
            report += "- Monitor for new trading patterns over time\n"
        
        report += "- Continue building knowledge base with new market insights\n"
        
        return report


def create_trade_analysis_workflow(postgres_agent, knowledge_base: DocumentKnowledgeBase) -> TradeAnalysisWorkflow:
    """Factory function to create the trade analysis workflow"""
    return TradeAnalysisWorkflow(postgres_agent, knowledge_base) 