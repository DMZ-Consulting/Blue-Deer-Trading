#!/usr/bin/env python3
"""
Trade Report Search Agent

This agent specializes in searching, retrieving, and analyzing saved trade analysis reports
from the hybrid storage system (SQLite + LanceDB). It can answer questions about trading
performance, patterns, and provide insights from historical trade data.
"""

import sys
import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.append(".")

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import Toolkit
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.document import DocumentKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.utils.pprint import pprint_run_response
from dotenv import load_dotenv

load_dotenv()

# --- Storage Configuration (same as controlled_trade_analysis.py) ---
SQLITE_DB_PATH = "./tmp/trade_analysis_storage.db"
LANCEDB_URI = "./tmp/trade_analysis_reports_lancedb"


class TradeReportSearchTools(Toolkit):
    """
    Tools for searching and analyzing saved trade analysis reports
    """
    
    def __init__(
        self,
        sqlite_db_path: str = SQLITE_DB_PATH,
        lancedb_uri: str = LANCEDB_URI,
        **kwargs
    ):
        self.sqlite_db_path = sqlite_db_path
        self.lancedb_uri = lancedb_uri
        self.conn = None
        self.knowledge_base = None
        
        tools = [
            self.search_reports_by_query,
            self.get_report_by_id,
            self.get_reports_by_symbol,
            self.get_performance_summary,
            self.find_similar_trades,
            self.analyze_trading_patterns,
            self.get_recent_reports
        ]
        
        super().__init__(name="TradeReportSearchTools", tools=tools, **kwargs)
        self._connect_to_storage()
    
    def _connect_to_storage(self):
        """Connect to the storage systems"""
        try:
            # Connect to SQLite
            self.conn = sqlite3.connect(self.sqlite_db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Connect to LanceDB knowledge base
            self.knowledge_base = DocumentKnowledgeBase(
                documents=[],
                vector_db=LanceDb(
                    table_name="trade_analysis_reports",
                    uri=self.lancedb_uri,
                    search_type=SearchType.hybrid,
                    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
                ),
            )
            self.knowledge_base.load(recreate=False)
            
        except Exception as e:
            print(f"Warning: Could not connect to storage: {e}")
    
    def search_reports_by_query(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search trade analysis reports using semantic search on content.
        
        Args:
            query: Search query (e.g., "high performing NVDA trades", "losing trades with high volatility")
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        if not self.knowledge_base:
            return {"success": False, "error": "Knowledge base not available"}
        
        try:
            # Perform semantic search
            search_results = self.knowledge_base.search(query, num_documents=limit)
            
            results = []
            for doc in search_results:
                # Extract metadata
                metadata = doc.meta_data or {}
                results.append({
                    "report_id": metadata.get("report_id"),
                    "trade_id": metadata.get("trade_id"),
                    "strategy_type": metadata.get("strategy_type"),
                    "performance_score": metadata.get("performance_score"),
                    "total_return_pct": metadata.get("total_return_pct"),
                    "market_trend": metadata.get("market_trend"),
                    "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    "relevance_score": getattr(doc, 'score', 0)
                })
            
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results
            }
            
        except Exception as e:
            return {"success": False, "error": f"Search failed: {e}"}
    
    def get_report_by_id(self, report_id: str) -> Dict[str, Any]:
        """
        Get a specific trade analysis report by its ID.
        
        Args:
            report_id: The report ID to retrieve
            
        Returns:
            Dictionary with the complete report data
        """
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM trade_analysis_reports 
                WHERE report_id = ?
            """, (report_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": f"Report {report_id} not found"}
            
            # Convert row to dictionary
            report_data = dict(row)
            
            # Parse the JSON report if available
            if report_data.get("full_report_json"):
                try:
                    report_data["parsed_report"] = json.loads(report_data["full_report_json"])
                except json.JSONDecodeError:
                    report_data["parsed_report"] = None
            
            return {
                "success": True,
                "report": report_data
            }
            
        except Exception as e:
            return {"success": False, "error": f"Database query failed: {e}"}
    
    def get_reports_by_symbol(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get all trade analysis reports for a specific symbol.
        
        Args:
            symbol: Stock symbol (e.g., "NVDA", "AAPL")
            limit: Maximum number of reports to return
            
        Returns:
            Dictionary with reports for the symbol
        """
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT report_id, trade_id, strategy_type, performance_score, 
                       total_return_pct, total_return_dollars, holding_period_days,
                       win_loss_classification, analysis_timestamp
                FROM trade_analysis_reports 
                WHERE symbol = ? 
                ORDER BY analysis_timestamp DESC
                LIMIT ?
            """, (symbol, limit))
            
            rows = cursor.fetchall()
            reports = [dict(row) for row in rows]
            
            # Calculate summary statistics
            if reports:
                total_returns = [r["total_return_pct"] for r in reports if r["total_return_pct"] is not None]
                win_count = sum(1 for r in reports if r["win_loss_classification"] == "WIN")
                
                summary = {
                    "total_trades": len(reports),
                    "win_rate": (win_count / len(reports) * 100) if reports else 0,
                    "avg_return_pct": sum(total_returns) / len(total_returns) if total_returns else 0,
                    "best_return_pct": max(total_returns) if total_returns else 0,
                    "worst_return_pct": min(total_returns) if total_returns else 0
                }
            else:
                summary = {"total_trades": 0}
            
            return {
                "success": True,
                "symbol": symbol,
                "summary": summary,
                "reports": reports
            }
            
        except Exception as e:
            return {"success": False, "error": f"Database query failed: {e}"}
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get a performance summary of all trades from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with performance metrics and statistics
        """
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            cursor = self.conn.cursor()
            
            # Get overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    AVG(performance_score) as avg_performance_score,
                    AVG(total_return_pct) as avg_return_pct,
                    SUM(CASE WHEN win_loss_classification = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN win_loss_classification = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    MAX(total_return_pct) as best_return,
                    MIN(total_return_pct) as worst_return,
                    AVG(holding_period_days) as avg_holding_period
                FROM trade_analysis_reports 
                WHERE analysis_timestamp >= datetime('now', '-{} days')
            """.format(days))
            
            stats = dict(cursor.fetchone())
            
            # Calculate win rate
            total_trades = stats["total_trades"] or 0
            wins = stats["wins"] or 0
            stats["win_rate_pct"] = (wins / total_trades * 100) if total_trades > 0 else 0
            
            # Get strategy breakdown
            cursor.execute("""
                SELECT 
                    strategy_type,
                    COUNT(*) as count,
                    AVG(total_return_pct) as avg_return,
                    SUM(CASE WHEN win_loss_classification = 'WIN' THEN 1 ELSE 0 END) as wins
                FROM trade_analysis_reports 
                WHERE analysis_timestamp >= datetime('now', '-{} days')
                GROUP BY strategy_type
            """.format(days))
            
            strategy_stats = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                total_count = row_dict["count"]
                wins = row_dict["wins"] or 0
                row_dict["win_rate_pct"] = (wins / total_count * 100) if total_count > 0 else 0
                strategy_stats.append(row_dict)
            
            # Get recent top performers
            cursor.execute("""
                SELECT report_id, trade_id, symbol, total_return_pct, strategy_type
                FROM trade_analysis_reports 
                WHERE analysis_timestamp >= datetime('now', '-{} days')
                ORDER BY total_return_pct DESC
                LIMIT 5
            """.format(days))
            
            top_performers = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "period_days": days,
                "overall_stats": stats,
                "strategy_breakdown": strategy_stats,
                "top_performers": top_performers
            }
            
        except Exception as e:
            return {"success": False, "error": f"Performance analysis failed: {e}"}
    
    def find_similar_trades(self, trade_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Find trades similar to a given trade using semantic search.
        
        Args:
            trade_id: Reference trade ID to find similar trades for
            limit: Maximum number of similar trades to return
            
        Returns:
            Dictionary with similar trades and their similarity scores
        """
        # First get the reference trade's report content
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT full_report_json FROM trade_analysis_reports 
                WHERE trade_id = ?
            """, (trade_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": f"Trade {trade_id} not found"}
            
            # Extract key characteristics for search
            try:
                report_data = json.loads(row["full_report_json"])
                
                # Build search query from trade characteristics
                search_query = f"""
                strategy: {report_data.get('strategy_type', '')}
                market conditions: {report_data.get('market_conditions', {}).get('market_trend', '')}
                volatility: {report_data.get('market_conditions', {}).get('volatility_regime', '')}
                performance: {report_data.get('performance_metrics', {}).get('win_loss_classification', '')}
                """
                
                # Use semantic search to find similar trades
                results = self.search_reports_by_query(search_query, limit + 1)  # +1 to exclude self
                
                # Filter out the original trade
                if results.get("success"):
                    similar_trades = [
                        r for r in results["results"] 
                        if r["trade_id"] != trade_id
                    ][:limit]
                    
                    return {
                        "success": True,
                        "reference_trade_id": trade_id,
                        "similar_trades": similar_trades,
                        "search_query_used": search_query.strip()
                    }
                else:
                    return results
                    
            except json.JSONDecodeError:
                return {"success": False, "error": "Could not parse reference trade report"}
            
        except Exception as e:
            return {"success": False, "error": f"Similarity search failed: {e}"}
    
    def analyze_trading_patterns(self, pattern_type: str = "all") -> Dict[str, Any]:
        """
        Analyze patterns across all trade reports.
        
        Args:
            pattern_type: Type of pattern analysis ("volatility", "performance", "timing", "all")
            
        Returns:
            Dictionary with pattern analysis results
        """
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            patterns = {}
            
            # Volatility regime patterns
            if pattern_type in ["volatility", "all"]:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT 
                        volatility_regime,
                        COUNT(*) as trade_count,
                        AVG(total_return_pct) as avg_return,
                        SUM(CASE WHEN win_loss_classification = 'WIN' THEN 1 ELSE 0 END) as wins
                    FROM trade_analysis_reports 
                    WHERE volatility_regime IS NOT NULL
                    GROUP BY volatility_regime
                """)
                
                volatility_patterns = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    total = row_dict["trade_count"]
                    wins = row_dict["wins"] or 0
                    row_dict["win_rate_pct"] = (wins / total * 100) if total > 0 else 0
                    volatility_patterns.append(row_dict)
                
                patterns["volatility_patterns"] = volatility_patterns
            
            # Market trend patterns
            if pattern_type in ["performance", "all"]:
                cursor.execute("""
                    SELECT 
                        market_trend,
                        COUNT(*) as trade_count,
                        AVG(total_return_pct) as avg_return,
                        SUM(CASE WHEN win_loss_classification = 'WIN' THEN 1 ELSE 0 END) as wins
                    FROM trade_analysis_reports 
                    WHERE market_trend IS NOT NULL
                    GROUP BY market_trend
                """)
                
                trend_patterns = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    total = row_dict["trade_count"]
                    wins = row_dict["wins"] or 0
                    row_dict["win_rate_pct"] = (wins / total * 100) if total > 0 else 0
                    trend_patterns.append(row_dict)
                
                patterns["trend_patterns"] = trend_patterns
            
            # Risk management grade patterns
            if pattern_type in ["timing", "all"]:
                cursor.execute("""
                    SELECT 
                        risk_management_grade,
                        COUNT(*) as trade_count,
                        AVG(total_return_pct) as avg_return,
                        AVG(holding_period_days) as avg_holding_period
                    FROM trade_analysis_reports 
                    WHERE risk_management_grade IS NOT NULL
                    GROUP BY risk_management_grade
                """)
                
                risk_patterns = [dict(row) for row in cursor.fetchall()]
                patterns["risk_management_patterns"] = risk_patterns
            
            return {
                "success": True,
                "pattern_type": pattern_type,
                "patterns": patterns,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Pattern analysis failed: {e}"}
    
    def get_recent_reports(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get the most recent trade analysis reports.
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            Dictionary with recent reports
        """
        if not self.conn:
            return {"success": False, "error": "Database not available"}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT report_id, trade_id, symbol, strategy_type, 
                       performance_score, total_return_pct, win_loss_classification,
                       analysis_timestamp
                FROM trade_analysis_reports 
                ORDER BY analysis_timestamp DESC
                LIMIT ?
            """, (limit,))
            
            reports = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "recent_reports": reports,
                "count": len(reports)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Database query failed: {e}"}


def create_trade_report_search_agent():
    """
    Create a specialized agent for searching and analyzing trade reports.
    """
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        name="TradeReportSearchAgent",
        role="Trade Analysis Report Specialist",
        tools=[TradeReportSearchTools()],
        instructions=[
            "You are a specialized agent for searching and analyzing saved trade analysis reports.",
            "You can search reports by content, symbol, performance metrics, and patterns.",
            "Always provide actionable insights and clear summaries when analyzing reports.",
            "When showing performance data, include both percentages and absolute values where relevant.",
            "Identify trends, patterns, and key learning opportunities from the trade data.",
            "Be concise but comprehensive in your analysis.",
            "",
            "SEARCH CAPABILITIES:",
            "- Semantic search by content (strategies, market conditions, outcomes)",
            "- Filter by symbol, performance, time period",
            "- Find similar trades based on characteristics", 
            "- Analyze patterns across all trades",
            "",
            "ANALYSIS FOCUS:",
            "- Performance metrics and win rates",
            "- Strategy effectiveness",
            "- Market condition correlations",
            "- Risk management insights",
            "- Trading pattern identification"
        ],
        show_tool_calls=True,
        markdown=True,
        debug_mode=True
    )
    
    return agent


def test_trade_report_search():
    """Test the trade report search agent"""
    print("🔍 Testing Trade Report Search Agent")
    print("=" * 60)
    
    agent = create_trade_report_search_agent()
    
    # Test queries
    test_queries = [
        "Show me a performance summary of all trades from the last 30 days",
        "Find all NVDA trades and analyze their performance", 
        "What are the recent trade reports?",
        "Search for high-performing trades with good risk management",
        "Analyze trading patterns across different market conditions"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: {query}")
        print("-" * 40)
        
        try:
            response = agent.run(query)
            print("✅ Response:")
            pprint_run_response(response)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    print("=" * 60)


if __name__ == "__main__":
    test_trade_report_search() 