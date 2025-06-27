"""
Trade Analysis Workflow using Agno

This script defines a workflow that uses three specialized agents to analyze stock trades.
It replaces the previous team-based approach to provide more explicit control over the
analysis process and data storage.

Workflow Steps:
1. Database Agent: Retrieves trade data from a PostgreSQL database.
2. Theta Data Agent: Fetches comprehensive historical options market data from the Theta Data API.
3. Analysis Agent: Synthesizes the data into a comprehensive TradeAnalysisReport.
4. Storage: The final report is saved to a hybrid storage system (SQLite and LanceDB).
"""
import sys
sys.path.append(".")
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Iterator

from dotenv import load_dotenv
from agno.agent import Agent
from agno.document.base import Document
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.document import DocumentKnowledgeBase
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.workflow import Workflow, RunResponse
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from pydantic import BaseModel, Field

# Import agents and data models from other files
from agents.theta_data_agent import get_theta_data_agent
from agents.trade_analysis_specialist import create_trade_analysis_specialist, TradeAnalysisReport
from agents.postgres_agent import create_database_agent

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

# --- Database and Storage Configuration ---
SQLITE_DB_PATH = "./tmp/trade_analysis_storage.db"
LANCEDB_URI = "./tmp/trade_analysis_reports_lancedb"


class TradeAnalysisDB:
    """
    Manages the hybrid storage for trade analysis reports, combining
    a structured SQLite database with a searchable LanceDB vector store.
    """

    def __init__(self, db_path: str, lancedb_uri: str):
        self.db_path = db_path
        self.lancedb_uri = lancedb_uri
        self.conn = None
        self.knowledge_base = None

    def connect(self):
        """Establish connections to SQLite and initialize LanceDB."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()

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
            print("✅ Database and knowledge base connected successfully.")
        except Exception as e:
            print(f"❌ Failed to connect to databases: {e}")
            raise

    def create_tables(self):
        """Create the necessary tables in the SQLite database."""
        if not self.conn:
            return
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_analysis_reports (
            report_id TEXT PRIMARY KEY,
            trade_id TEXT,
            symbol TEXT,
            strategy_type TEXT,
            performance_score INTEGER,
            total_return_pct REAL,
            total_return_dollars REAL,
            holding_period_days INTEGER,
            win_loss_classification TEXT,
            volatility_regime TEXT,
            market_trend TEXT,
            risk_management_grade TEXT,
            confidence_level INTEGER,
            analysis_timestamp TEXT,
            full_report_json TEXT
        )
        """)
        self.conn.commit()

    def save_report(self, report: TradeAnalysisReport, trade_id: str):
        """
        Saves a trade analysis report to both SQLite and LanceDB.
        """
        if not self.conn or not self.knowledge_base:
            raise ConnectionError("Database not connected. Call connect() first.")

        report_id = f"report_{trade_id}_{datetime.now().strftime('%Y%m%d%HM%S')}"
        analysis_timestamp = datetime.now().isoformat()

        # --- 1. Save to Structured DB (SQLite) ---
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO trade_analysis_reports (
                report_id, trade_id, symbol, strategy_type, performance_score,
                total_return_pct, total_return_dollars, holding_period_days,
                win_loss_classification, volatility_regime, market_trend,
                risk_management_grade, confidence_level, analysis_timestamp,
                full_report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                trade_id,
                # These fields need to be present in your TradeAnalysisReport or passed in
                "N/A",  # Placeholder for symbol
                report.strategy_type,
                report.performance_score,
                report.performance_metrics.total_return_pct,
                report.performance_metrics.total_return_dollars,
                report.performance_metrics.holding_period_days,
                report.performance_metrics.win_loss_classification,
                report.market_conditions.volatility_regime,
                report.market_conditions.market_trend,
                report.risk_management_grade,
                report.confidence_level,
                analysis_timestamp,
                report.model_dump_json()
            ))
            self.conn.commit()
            print(f"✅ Report {report_id} saved to SQLite.")
        except Exception as e:
            print(f"❌ Failed to save report to SQLite: {e}")
            self.conn.rollback()

        # --- 2. Save to Vector DB (LanceDB) for searching ---
        try:
            doc_content = f"""
            Executive Summary: {report.executive_summary}
            Strengths: {', '.join(report.key_strengths)}
            Weaknesses: {', '.join(report.key_weaknesses)}
            Recommendations: {', '.join(report.actionable_recommendations)}
            """
            document = Document(
                content=doc_content,
                meta_data={
                    "report_id": report_id,
                    "trade_id": trade_id,
                    "strategy_type": report.strategy_type,
                    "performance_score": report.performance_score,
                    "total_return_pct": report.performance_metrics.total_return_pct,
                    "market_trend": report.market_conditions.market_trend,
                    "analysis_timestamp": analysis_timestamp,
                }
            )
            self.knowledge_base.documents.append(document)
            self.knowledge_base.load(recreate=False)  # Append new document
            print(f"✅ Report {report_id} saved to LanceDB.")
        except Exception as e:
            print(f"❌ Failed to save report to LanceDB: {e}")

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")


class ControlledTradeAnalysisWorkflow(Workflow):
    """
    Orchestrates the trade analysis process from data retrieval to storage.
    """
    database_agent: Agent
    theta_data_agent: Agent
    analysis_agent: Agent
    db_manager: TradeAnalysisDB

    def __init__(
        self,
        db_path: str = SQLITE_DB_PATH,
        lancedb_uri: str = LANCEDB_URI,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.database_agent = create_database_agent(
            name="TradeDBSpecialist",
            role="Retrieve trade data for analysis",
        )
        self.theta_data_agent = get_theta_data_agent()
        self.analysis_agent = create_trade_analysis_specialist()
        self.db_manager = TradeAnalysisDB(db_path, lancedb_uri)
        self.db_manager.connect()

    def run(self, trade_id: str) -> Iterator[RunResponse]:
        """
        Executes the full trade analysis workflow.
        
        Args:
            trade_id: The ID of the trade to analyze.
        
        Yields:
            WorkflowRun objects indicating the progress and results.
        """
        logger.info(f"Starting analysis for trade: {trade_id}")

        # --- Step 1: Get Trade Data ---
        trade_data_response = self.database_agent.run(f"Get complete trade data for trade_id: {trade_id}")
        if not trade_data_response or not trade_data_response.content:
            logger.error(f"Failed to get data for trade {trade_id}")
            return
        
        #yield trade_data_response

        trade_data_str = trade_data_response.content

        # --- Step 2: Get Market Data ---
        market_data_prompt = f"""
        Given the following trade data, fetch comprehensive market context using Theta Data tools.
        Extract the options contract details and retrieve historical data including OHLC, trades, Greeks, and implied volatility.
        Use AI-friendly compression to optimize data for analysis.
        
        Trade Data: {trade_data_str}
        """
        market_data_response = self.theta_data_agent.run(market_data_prompt)
        if not market_data_response or not market_data_response.content:
            logger.error("Failed to get market data.")
            return

        #yield market_data_response

        market_data_str = market_data_response.content

        # --- Step 3: Synthesize and Analyze ---
        analysis_prompt = f"""
        Analyze the trade using the provided data and generate a comprehensive report.

        **TRADE DATA:**
        {trade_data_str}

        **MARKET CONTEXT:**
        {market_data_str}
        """
        analysis_response = self.analysis_agent.run(analysis_prompt)
        if not analysis_response or not isinstance(analysis_response.content, TradeAnalysisReport):
            logger.error("Failed to generate analysis report.")
            return

        final_report: TradeAnalysisReport = analysis_response.content

        # --- Step 4: Save the Report ---
        try:
            self.db_manager.save_report(final_report, trade_id)
            logger.info("Analysis complete and report saved.")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        finally:
            self.db_manager.close()

        return analysis_response


if __name__ == "__main__":
    def test_trade_analysis_workflow():
        """Test the trade analysis workflow."""
        print("🚀 Testing Trade Analysis Workflow")
        print("=" * 60)

        workflow = ControlledTradeAnalysisWorkflow()
        
        test_trade_id = "GNUMT0M0"
        
        print(f"\n🧪 Running workflow for trade: {test_trade_id}...")
        print("-" * 40)

        final_run = None
        workflow_response: Iterator[RunResponse] = workflow.run(trade_id=test_trade_id)
        pprint_run_response(workflow_response)

        print("-" * 40)
        
        if final_run and final_run.type == "success":
            print("✅ Workflow completed successfully!")
            final_report = final_run.content
            if isinstance(final_report, TradeAnalysisReport):
                print("\n--- EXECUTIVE SUMMARY ---")
                print(final_report.executive_summary)
                print("\n--- RECOMMENDATIONS ---")
                for rec in final_report.actionable_recommendations:
                    print(f"- {rec}")
        else:
            print("❌ Workflow failed or did not complete.")

        print("=" * 60)

    # Run the test
    test_trade_analysis_workflow() 