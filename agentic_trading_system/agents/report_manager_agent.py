"""
Trade Report Manager Agent

This agent specializes in managing, searching, and retrieving historical trade analysis reports.
It provides tools for other agents and workflows to access stored analysis data for pattern
recognition, performance tracking, and strategy improvement.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
from datetime import datetime, timedelta

# Import the report storage class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from teams.polygon_team import TradeAnalysisReportStorage

class ReportsToolKit(Tool):
    """Tool for searching historical trade analysis reports"""
    
    def __init__(self):
        super().__init__(
            name="search_trade_reports",
            description="Search historical trade analysis reports by query text, symbol, strategy, or other criteria"
        )
        self.storage = TradeAnalysisReportStorage()
    
    def run(self, query: str, num_results: int = 5, symbol: str = None, 
            strategy_type: str = None, win_loss: str = None, 
            min_performance_score: int = None) -> str:
        """
        Search for trade analysis reports
        
        Args:
            query: Search query text (e.g., "profitable options trades", "high volatility")
            num_results: Number of results to return (default: 5)
            symbol: Filter by specific symbol (e.g., "NVDA", "AAPL")
            strategy_type: Filter by strategy type
            win_loss: Filter by outcome ("Win", "Loss", "Breakeven")
            min_performance_score: Filter by minimum performance score (1-10)
        """
        try:
            # Build filters
            filters = {}
            if symbol:
                filters["symbol"] = symbol
            if strategy_type:
                filters["strategy_type"] = strategy_type
            if win_loss:
                filters["win_loss"] = win_loss
            if min_performance_score:
                filters["performance_score"] = {"$gte": min_performance_score}
            
            # Perform search
            results = self.storage.search_reports(
                query=query,
                num_results=num_results,
                filters=filters if filters else None
            )
            
            if not results:
                return f"No reports found for query: '{query}' with the specified filters."
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                metadata = result.get("metadata", {})
                formatted_results.append(f"""
📊 **Report {i}:**
- **Trade ID:** {metadata.get('trade_id', 'N/A')}
- **Symbol:** {metadata.get('symbol', 'N/A')}
- **Strategy:** {metadata.get('strategy_type', 'N/A')}
- **Outcome:** {metadata.get('win_loss', 'N/A')}
- **Performance Score:** {metadata.get('performance_score', 'N/A')}/10
- **P&L:** ${metadata.get('profit_loss', 0):.2f}
- **Analysis Date:** {metadata.get('analysis_date', 'N/A')}
- **Relevance Score:** {result.get('score', 0):.3f}
""")
            
            return f"Found {len(results)} reports:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error searching reports: {str(e)}"

class GetReportToolKit(Tool):
    """Tool for retrieving a specific trade report by ID"""
    
    def __init__(self):
        super().__init__(
            name="get_trade_report",
            description="Retrieve a specific trade analysis report by trade ID"
        )
        self.storage = TradeAnalysisReportStorage()
    
    def run(self, trade_id: str) -> str:
        """
        Get a specific trade analysis report
        
        Args:
            trade_id: The trade ID to retrieve
        """
        try:
            report = self.storage.get_report_by_trade_id(trade_id)
            
            if not report:
                return f"No report found for trade ID: {trade_id}"
            
            content = report.get("content", "")
            metadata = report.get("metadata", {})
            
            return f"""📋 **Trade Analysis Report**

{content}

**Report Metadata:**
- Analysis Date: {metadata.get('analysis_date', 'N/A')}
- Symbol: {metadata.get('symbol', 'N/A')}
- Strategy: {metadata.get('strategy_type', 'N/A')}
- Performance Score: {metadata.get('performance_score', 'N/A')}/10
- P&L: ${metadata.get('profit_loss', 0):.2f}
- Outcome: {metadata.get('win_loss', 'N/A')}
"""
            
        except Exception as e:
            return f"Error retrieving report for trade {trade_id}: {str(e)}"

class PerformanceAnalysisToolKit(Tool):
    """Tool for analyzing performance patterns across multiple reports"""
    
    def __init__(self):
        super().__init__(
            name="analyze_performance_patterns",
            description="Analyze performance patterns across historical reports for insights and trends"
        )
        self.storage = TradeAnalysisReportStorage()
    
    def run(self, symbol: str = None, strategy_type: str = None, 
            analysis_type: str = "summary") -> str:
        """
        Analyze performance patterns from historical reports
        
        Args:
            symbol: Focus analysis on specific symbol
            strategy_type: Focus analysis on specific strategy type
            analysis_type: Type of analysis ("summary", "detailed", "trends")
        """
        try:
            # Get relevant reports
            reports = self.storage.get_performance_insights(
                symbol=symbol,
                strategy_type=strategy_type
            )
            
            if not reports:
                filter_desc = f" for {symbol}" if symbol else ""
                filter_desc += f" {strategy_type} strategy" if strategy_type else ""
                return f"No reports found{filter_desc}"
            
            # Extract metrics for analysis
            metrics = []
            for report in reports:
                metadata = report.get("metadata", {})
                if metadata:
                    metrics.append({
                        "trade_id": metadata.get("trade_id"),
                        "symbol": metadata.get("symbol"),
                        "strategy": metadata.get("strategy_type"),
                        "performance_score": metadata.get("performance_score", 0),
                        "profit_loss": metadata.get("profit_loss", 0),
                        "win_loss": metadata.get("win_loss"),
                        "analysis_date": metadata.get("analysis_date")
                    })
            
            if not metrics:
                return "No valid metrics found in reports"
            
            # Calculate summary statistics
            total_trades = len(metrics)
            wins = len([m for m in metrics if m["win_loss"] == "Win"])
            losses = len([m for m in metrics if m["win_loss"] == "Loss"])
            breakevens = len([m for m in metrics if m["win_loss"] == "Breakeven"])
            
            total_pnl = sum(m["profit_loss"] for m in metrics)
            avg_performance_score = sum(m["performance_score"] for m in metrics) / total_trades
            
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            # Generate analysis based on type
            if analysis_type == "summary":
                return f"""📈 **Performance Analysis Summary**

**Overview:**
- Total Trades Analyzed: {total_trades}
- Win Rate: {win_rate:.1f}% ({wins} wins, {losses} losses, {breakevens} breakevens)
- Total P&L: ${total_pnl:.2f}
- Average Performance Score: {avg_performance_score:.1f}/10

**Filter Applied:**
- Symbol: {symbol or 'All'}
- Strategy: {strategy_type or 'All'}

**Quick Insights:**
- {"Strong" if win_rate >= 60 else "Moderate" if win_rate >= 40 else "Weak"} win rate
- {"Profitable" if total_pnl > 0 else "Unprofitable"} overall performance
- {"High" if avg_performance_score >= 7 else "Medium" if avg_performance_score >= 5 else "Low"} quality trades on average
"""
            
            elif analysis_type == "detailed":
                # Top and bottom performers
                sorted_by_pnl = sorted(metrics, key=lambda x: x["profit_loss"], reverse=True)
                best_trade = sorted_by_pnl[0] if sorted_by_pnl else None
                worst_trade = sorted_by_pnl[-1] if sorted_by_pnl else None
                
                return f"""📊 **Detailed Performance Analysis**

**Summary Statistics:**
- Total Trades: {total_trades}
- Win Rate: {win_rate:.1f}%
- Total P&L: ${total_pnl:.2f}
- Average Performance Score: {avg_performance_score:.1f}/10

**Best Trade:**
- Trade ID: {best_trade["trade_id"] if best_trade else "N/A"}
- P&L: ${best_trade["profit_loss"] if best_trade else 0:.2f}
- Performance Score: {best_trade["performance_score"] if best_trade else 0}/10

**Worst Trade:**
- Trade ID: {worst_trade["trade_id"] if worst_trade else "N/A"}
- P&L: ${worst_trade["profit_loss"] if worst_trade else 0:.2f}
- Performance Score: {worst_trade["performance_score"] if worst_trade else 0}/10

**Performance Distribution:**
- High Quality (Score 8-10): {len([m for m in metrics if m["performance_score"] >= 8])} trades
- Medium Quality (Score 5-7): {len([m for m in metrics if 5 <= m["performance_score"] < 8])} trades
- Low Quality (Score 1-4): {len([m for m in metrics if m["performance_score"] < 5])} trades
"""
            
            else:  # trends
                return f"""📈 **Performance Trends Analysis**

**Recent Performance:** (Last {min(10, total_trades)} trades)
- Win Rate: {win_rate:.1f}%
- Average P&L per Trade: ${total_pnl/total_trades:.2f}
- Average Performance Score: {avg_performance_score:.1f}/10

**Key Patterns:**
- Most Common Outcome: {max(["Win", "Loss", "Breakeven"], key=lambda x: len([m for m in metrics if m["win_loss"] == x]))}
- Strategy Performance: {strategy_type or "Mixed strategies"}
- Symbol Performance: {symbol or "Multiple symbols"}

**Recommendations:**
- {"Continue current approach" if win_rate >= 50 and total_pnl > 0 else "Review and adjust strategy"}
- {"Focus on quality" if avg_performance_score < 6 else "Maintain quality standards"}
"""
            
        except Exception as e:
            return f"Error analyzing performance patterns: {str(e)}"

class CompareReportsToolKit(Tool):
    """Tool for comparing multiple trade reports"""
    
    def __init__(self):
        super().__init__(
            name="compare_trade_reports",
            description="Compare multiple trade reports to identify patterns and differences"
        )
        self.storage = TradeAnalysisReportStorage()
    
    def run(self, trade_ids: str) -> str:
        """
        Compare multiple trade reports
        
        Args:
            trade_ids: Comma-separated list of trade IDs to compare
        """
        try:
            trade_id_list = [tid.strip() for tid in trade_ids.split(",")]
            
            if len(trade_id_list) < 2:
                return "Please provide at least 2 trade IDs separated by commas"
            
            reports = []
            for trade_id in trade_id_list:
                report = self.storage.get_report_by_trade_id(trade_id)
                if report:
                    reports.append((trade_id, report))
                else:
                    return f"Report not found for trade ID: {trade_id}"
            
            if len(reports) < 2:
                return "Could not find enough reports for comparison"
            
            # Extract comparison metrics
            comparison = []
            for trade_id, report in reports:
                metadata = report.get("metadata", {})
                comparison.append({
                    "trade_id": trade_id,
                    "symbol": metadata.get("symbol", "N/A"),
                    "strategy": metadata.get("strategy_type", "N/A"),
                    "performance_score": metadata.get("performance_score", 0),
                    "profit_loss": metadata.get("profit_loss", 0),
                    "win_loss": metadata.get("win_loss", "N/A"),
                    "analysis_date": metadata.get("analysis_date", "N/A")
                })
            
            # Generate comparison table
            result = "🔍 **Trade Comparison Analysis**\n\n"
            
            for i, trade in enumerate(comparison, 1):
                result += f"""**Trade {i} - {trade['trade_id']}:**
- Symbol: {trade['symbol']}
- Strategy: {trade['strategy']}
- Performance Score: {trade['performance_score']}/10
- P&L: ${trade['profit_loss']:.2f}
- Outcome: {trade['win_loss']}
- Analysis Date: {trade['analysis_date']}

"""
            
            # Add insights
            best_performer = max(comparison, key=lambda x: x["profit_loss"])
            worst_performer = min(comparison, key=lambda x: x["profit_loss"])
            
            result += f"""**Key Insights:**
- Best Performer: {best_performer['trade_id']} (${best_performer['profit_loss']:.2f})
- Worst Performer: {worst_performer['trade_id']} (${worst_performer['profit_loss']:.2f})
- Performance Range: {min(t['performance_score'] for t in comparison)}-{max(t['performance_score'] for t in comparison)}/10
- Strategies Compared: {', '.join(set(t['strategy'] for t in comparison))}
- Symbols Compared: {', '.join(set(t['symbol'] for t in comparison))}
"""
            
            return result
            
        except Exception as e:
            return f"Error comparing reports: {str(e)}"

def create_report_manager_agent(model_provider: str = "openai") -> Agent:
    """
    Create a specialized agent for managing and analyzing trade reports
    
    Args:
        model_provider: Model provider to use ("openai" or "anthropic")
    
    Returns:
        Configured report manager agent
    """
    
    # Choose model based on provider
    if model_provider.lower() == "anthropic":
        model = Claude(id="claude-3-5-sonnet-20241022")
    else:
        model = OpenAIChat(id="gpt-4")
    
    return Agent(
        name="Trade Report Manager",
        model=model,
        role="Specialist in managing and analyzing historical trade analysis reports",
        instructions=[
            "🎯 MISSION: Manage, search, and analyze historical trade analysis reports",
            "",
            "🔍 CORE CAPABILITIES:",
            "• Search reports by text, symbol, strategy, or performance metrics",
            "• Retrieve specific reports by trade ID",
            "• Analyze performance patterns and trends across multiple reports",
            "• Compare multiple trades to identify patterns and insights",
            "• Provide data-driven insights for strategy improvement",
            "",
            "📊 ANALYSIS EXPERTISE:",
            "• Performance trend identification",
            "• Strategy effectiveness assessment",
            "• Symbol-specific performance patterns",
            "• Risk-reward analysis across trades",
            "• Win rate and profitability metrics",
            "",
            "🎯 SEARCH STRATEGIES:",
            "• Use specific symbols, strategies, or outcomes for targeted searches",
            "• Combine text queries with metadata filters for precise results",
            "• Analyze time periods and market conditions for context",
            "• Focus on high-performing trades for pattern learning",
            "",
            "💡 INSIGHTS DELIVERY:",
            "• Provide clear, actionable insights from report analysis",
            "• Identify successful patterns that can be replicated",
            "• Highlight areas for improvement based on historical data",
            "• Support decision-making with data-driven recommendations",
            "",
            "🤝 COLLABORATION:",
            "• Work with other agents to provide historical context",
            "• Support workflow decisions with relevant historical data",
            "• Facilitate learning from past trades and strategies",
            "• Enable pattern recognition across trading activities"
        ],
        tools=[
            ReportsToolKit(),
            GetReportToolKit(),
            PerformanceAnalysisToolKit(),
            CompareReportsToolKit()
        ],
        markdown=True,
        show_tool_calls=True,
        add_datetime_to_instructions=True,
    )

if __name__ == "__main__":
    """Test the report manager agent"""
    
    print("🚀 Testing Trade Report Manager Agent")
    print("=" * 50)
    
    # Create the agent
    agent = create_report_manager_agent()
    
    # Test searches and analysis
    test_queries = [
        "Search for all NVDA trades",
        "Show me the most profitable trades",
        "Get performance analysis for options strategies",
        "Find trades with high performance scores"
    ]
    
    for query in test_queries:
        print(f"\n🧪 Test Query: {query}")
        print("-" * 30)
        try:
            response = agent.run(query)
            print(response.content)
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 30) 