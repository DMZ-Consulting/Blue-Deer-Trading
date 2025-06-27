"""
Report Access Workflow

This workflow provides standardized access to stored trade analysis reports for other workflows 
and agents. It implements proper agno workflow patterns for report retrieval, search, and analysis.
"""

from agno.workflow import Workflow
from agno.workflow.context import WorkflowContext
from agno.workflow.responses import RunResponse, RunEvent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.document import DocumentKnowledgeBase
from agno.document.base import Document
from agents.report_manager_agent import create_report_manager_agent
from teams.polygon_team import TradeAnalysisReportStorage
from typing import Iterator, Dict, List, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field

class ReportAccessRequest(BaseModel):
    """Request model for accessing reports"""
    request_type: str = Field(..., description="Type of request: 'search', 'get', 'analyze', 'compare'")
    trade_id: Optional[str] = Field(None, description="Specific trade ID to retrieve")
    trade_ids: Optional[List[str]] = Field(None, description="Multiple trade IDs for comparison")
    query: Optional[str] = Field(None, description="Search query text")
    symbol: Optional[str] = Field(None, description="Filter by symbol")
    strategy_type: Optional[str] = Field(None, description="Filter by strategy type")
    win_loss: Optional[str] = Field(None, description="Filter by outcome")
    min_performance_score: Optional[int] = Field(None, description="Minimum performance score")
    num_results: int = Field(5, description="Number of results to return")
    analysis_type: str = Field("summary", description="Analysis type: summary, detailed, trends")

class ReportAccessResponse(BaseModel):
    """Response model for report access"""
    success: bool = Field(..., description="Whether the request was successful")
    request_type: str = Field(..., description="Type of request processed")
    data: Dict[str, Any] = Field(..., description="Response data")
    message: str = Field(..., description="Human-readable message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ReportAccessWorkflow(Workflow):
    """Workflow for accessing and analyzing stored trade reports"""
    
    def __init__(
        self,
        model_provider: str = "anthropic",
        enable_caching: bool = True,
        storage_uri: str = "./tmp/report_access_workflow",
    ):
        """
        Initialize the report access workflow
        
        Args:
            model_provider: AI model provider ("anthropic" or "openai")
            enable_caching: Enable result caching for performance
            storage_uri: URI for workflow storage
        """
        super().__init__(
            name="Report Access Workflow",
            model=Claude(id="claude-3-5-sonnet-20241022") if model_provider == "anthropic" 
                  else OpenAIChat(id="gpt-4"),
        )
        
        self.model_provider = model_provider
        self.enable_caching = enable_caching
        self.storage_uri = storage_uri
        
        # Initialize report storage
        self.report_storage = TradeAnalysisReportStorage()
        
        # Initialize report manager agent
        self.report_agent = create_report_manager_agent(model_provider)
        
        # Initialize caching if enabled
        self.cache = {} if enable_caching else None
        
        # Initialize workflow-specific knowledge base for storing access patterns
        try:
            self.workflow_kb = DocumentKnowledgeBase(
                documents=[],
                vector_db=LanceDb(
                    table_name="report_access_patterns",
                    uri=f"{storage_uri}/access_patterns",
                    search_type=SearchType.hybrid,
                    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
                ),
            )
            self.workflow_kb.load(recreate=False)
        except Exception as e:
            print(f"⚠️ Workflow knowledge base initialization: {e}")
            self.workflow_kb = None
    
    def _generate_cache_key(self, request: ReportAccessRequest) -> str:
        """Generate a cache key for the request"""
        key_data = {
            "type": request.request_type,
            "trade_id": request.trade_id,
            "query": request.query,
            "symbol": request.symbol,
            "strategy": request.strategy_type,
            "win_loss": request.win_loss,
            "min_score": request.min_performance_score,
            "num_results": request.num_results,
            "analysis_type": request.analysis_type
        }
        return str(hash(json.dumps(key_data, sort_keys=True)))
    
    def _log_access_pattern(self, request: ReportAccessRequest, response: ReportAccessResponse):
        """Log access patterns for workflow optimization"""
        if not self.workflow_kb:
            return
        
        try:
            access_log = {
                "timestamp": datetime.now().isoformat(),
                "request_type": request.request_type,
                "success": response.success,
                "query": request.query,
                "filters_used": {
                    "symbol": request.symbol,
                    "strategy": request.strategy_type,
                    "outcome": request.win_loss
                },
                "results_count": len(response.data.get("results", [])) if isinstance(response.data.get("results"), list) else 0
            }
            
            document = Document(
                content=f"Report access: {request.request_type} - {request.query or 'No query'} - Success: {response.success}",
                metadata=access_log
            )
            
            self.workflow_kb.documents.append(document)
            self.workflow_kb.load_document(document, upsert=True)
            
        except Exception as e:
            print(f"⚠️ Failed to log access pattern: {e}")
    
    def run(
        self,
        request: ReportAccessRequest,
        context: Optional[WorkflowContext] = None,
    ) -> Iterator[RunResponse]:
        """
        Execute the report access workflow
        
        Args:
            request: Report access request
            context: Optional workflow context
            
        Yields:
            RunResponse objects with progress updates and results
        """
        
        # Validate request
        yield RunResponse(
            event=RunEvent.workflow_started.value,
            content="🚀 Starting Report Access Workflow",
            metadata={"request_type": request.request_type}
        )
        
        # Check cache if enabled
        cache_key = None
        if self.cache is not None:
            cache_key = self._generate_cache_key(request)
            if cache_key in self.cache:
                cached_response = self.cache[cache_key]
                yield RunResponse(
                    event=RunEvent.run_response.value,
                    content=f"📋 Retrieved from cache: {cached_response.message}",
                    metadata={"cached": True, "data": cached_response.data}
                )
                return
        
        try:
            response_data = {}
            
            if request.request_type == "search":
                yield RunResponse(
                    event=RunEvent.workflow_running.value,
                    content=f"🔍 Searching reports with query: '{request.query}'"
                )
                
                # Build filters
                filters = {}
                if request.symbol:
                    filters["symbol"] = request.symbol
                if request.strategy_type:
                    filters["strategy_type"] = request.strategy_type
                if request.win_loss:
                    filters["win_loss"] = request.win_loss
                if request.min_performance_score:
                    filters["performance_score"] = {"$gte": request.min_performance_score}
                
                # Perform search
                results = self.report_storage.search_reports(
                    query=request.query or "",
                    num_results=request.num_results,
                    filters=filters if filters else None
                )
                
                response_data = {
                    "results": results,
                    "query": request.query,
                    "filters_applied": filters,
                    "total_found": len(results)
                }
                
                message = f"Found {len(results)} reports matching your search criteria"
                
            elif request.request_type == "get":
                if not request.trade_id:
                    raise ValueError("trade_id is required for 'get' request")
                
                yield RunResponse(
                    event=RunEvent.workflow_running.value,
                    content=f"📄 Retrieving report for trade ID: {request.trade_id}"
                )
                
                # Get specific report
                report = self.report_storage.get_report_by_trade_id(request.trade_id)
                
                if report:
                    response_data = {
                        "report": report,
                        "trade_id": request.trade_id
                    }
                    message = f"Successfully retrieved report for trade {request.trade_id}"
                else:
                    response_data = {"report": None, "trade_id": request.trade_id}
                    message = f"No report found for trade {request.trade_id}"
                
            elif request.request_type == "analyze":
                yield RunResponse(
                    event=RunEvent.workflow_running.value,
                    content=f"📊 Analyzing performance patterns - Type: {request.analysis_type}"
                )
                
                # Get performance insights
                reports = self.report_storage.get_performance_insights(
                    symbol=request.symbol,
                    strategy_type=request.strategy_type
                )
                
                if reports:
                    # Calculate analysis metrics
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
                    
                    # Generate analysis summary
                    total_trades = len(metrics)
                    wins = len([m for m in metrics if m["win_loss"] == "Win"])
                    total_pnl = sum(m["profit_loss"] for m in metrics)
                    avg_score = sum(m["performance_score"] for m in metrics) / total_trades if total_trades > 0 else 0
                    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                    
                    response_data = {
                        "analysis_type": request.analysis_type,
                        "total_trades": total_trades,
                        "win_rate": win_rate,
                        "total_pnl": total_pnl,
                        "average_performance_score": avg_score,
                        "metrics": metrics,
                        "filters": {
                            "symbol": request.symbol,
                            "strategy_type": request.strategy_type
                        }
                    }
                    
                    message = f"Analyzed {total_trades} trades - Win rate: {win_rate:.1f}%, Total P&L: ${total_pnl:.2f}"
                else:
                    response_data = {"analysis_type": request.analysis_type, "metrics": []}
                    message = "No reports found for analysis"
                
            elif request.request_type == "compare":
                if not request.trade_ids or len(request.trade_ids) < 2:
                    raise ValueError("At least 2 trade_ids are required for 'compare' request")
                
                yield RunResponse(
                    event=RunEvent.workflow_running.value,
                    content=f"🔍 Comparing {len(request.trade_ids)} trades"
                )
                
                # Get reports for comparison
                comparison_data = []
                for trade_id in request.trade_ids:
                    report = self.report_storage.get_report_by_trade_id(trade_id)
                    if report:
                        metadata = report.get("metadata", {})
                        comparison_data.append({
                            "trade_id": trade_id,
                            "symbol": metadata.get("symbol", "N/A"),
                            "strategy": metadata.get("strategy_type", "N/A"),
                            "performance_score": metadata.get("performance_score", 0),
                            "profit_loss": metadata.get("profit_loss", 0),
                            "win_loss": metadata.get("win_loss", "N/A"),
                            "analysis_date": metadata.get("analysis_date", "N/A")
                        })
                
                if comparison_data:
                    # Calculate comparison insights
                    best_performer = max(comparison_data, key=lambda x: x["profit_loss"])
                    worst_performer = min(comparison_data, key=lambda x: x["profit_loss"])
                    
                    response_data = {
                        "trades_compared": comparison_data,
                        "best_performer": best_performer,
                        "worst_performer": worst_performer,
                        "total_compared": len(comparison_data),
                        "performance_range": {
                            "min_score": min(t["performance_score"] for t in comparison_data),
                            "max_score": max(t["performance_score"] for t in comparison_data)
                        }
                    }
                    
                    message = f"Compared {len(comparison_data)} trades - Best: {best_performer['trade_id']} (${best_performer['profit_loss']:.2f})"
                else:
                    response_data = {"trades_compared": [], "message": "No reports found for comparison"}
                    message = "No reports found for the specified trade IDs"
                
            else:
                raise ValueError(f"Unknown request type: {request.request_type}")
            
            # Create response
            response = ReportAccessResponse(
                success=True,
                request_type=request.request_type,
                data=response_data,
                message=message,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "workflow_version": "1.0.0"
                }
            )
            
            # Cache result if enabled
            if self.cache is not None and cache_key:
                self.cache[cache_key] = response
            
            # Log access pattern
            self._log_access_pattern(request, response)
            
            yield RunResponse(
                event=RunEvent.run_response.value,
                content=f"✅ {message}",
                metadata={"success": True, "data": response_data}
            )
            
        except Exception as e:
            error_response = ReportAccessResponse(
                success=False,
                request_type=request.request_type,
                data={"error": str(e)},
                message=f"Error processing {request.request_type} request: {str(e)}",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
            yield RunResponse(
                event=RunEvent.run_response.value,
                content=f"❌ Error: {str(e)}",
                metadata={"success": False, "error": str(e)}
            )
        
        yield RunResponse(
            event=RunEvent.workflow_completed.value,
            content="🏁 Report Access Workflow Completed"
        )

# Convenience functions for easy workflow usage
def search_reports_workflow(
    query: str,
    symbol: str = None,
    strategy_type: str = None,
    num_results: int = 5
) -> Dict[str, Any]:
    """
    Convenience function to search reports using the workflow
    
    Args:
        query: Search query
        symbol: Optional symbol filter
        strategy_type: Optional strategy filter
        num_results: Number of results to return
    
    Returns:
        Dictionary with search results
    """
    workflow = ReportAccessWorkflow()
    request = ReportAccessRequest(
        request_type="search",
        query=query,
        symbol=symbol,
        strategy_type=strategy_type,
        num_results=num_results
    )
    
    results = list(workflow.run(request))
    final_result = results[-2] if len(results) > 1 else results[-1]  # Get result before completion
    return final_result.metadata.get("data", {})

def get_report_workflow(trade_id: str) -> Dict[str, Any]:
    """
    Convenience function to get a specific report using the workflow
    
    Args:
        trade_id: Trade ID to retrieve
    
    Returns:
        Dictionary with report data
    """
    workflow = ReportAccessWorkflow()
    request = ReportAccessRequest(
        request_type="get",
        trade_id=trade_id
    )
    
    results = list(workflow.run(request))
    final_result = results[-2] if len(results) > 1 else results[-1]
    return final_result.metadata.get("data", {})

def analyze_performance_workflow(
    symbol: str = None,
    strategy_type: str = None,
    analysis_type: str = "summary"
) -> Dict[str, Any]:
    """
    Convenience function to analyze performance using the workflow
    
    Args:
        symbol: Optional symbol filter
        strategy_type: Optional strategy filter
        analysis_type: Type of analysis to perform
    
    Returns:
        Dictionary with analysis results
    """
    workflow = ReportAccessWorkflow()
    request = ReportAccessRequest(
        request_type="analyze",
        symbol=symbol,
        strategy_type=strategy_type,
        analysis_type=analysis_type
    )
    
    results = list(workflow.run(request))
    final_result = results[-2] if len(results) > 1 else results[-1]
    return final_result.metadata.get("data", {})

if __name__ == "__main__":
    """Test the report access workflow"""
    
    print("🚀 Testing Report Access Workflow")
    print("=" * 50)
    
    # Test search functionality
    print("\n🔍 Testing Search:")
    search_result = search_reports_workflow(
        query="profitable options trades",
        num_results=3
    )
    print(f"Search found {search_result.get('total_found', 0)} results")
    
    # Test performance analysis
    print("\n📊 Testing Performance Analysis:")
    analysis_result = analyze_performance_workflow(
        analysis_type="summary"
    )
    print(f"Analysis of {analysis_result.get('total_trades', 0)} trades completed")
    
    print("\n✅ Report Access Workflow Tests Completed") 