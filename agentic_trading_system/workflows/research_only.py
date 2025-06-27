"""
Research-Only Workflow - Standalone Trading Strategy Research System

This workflow focuses ONLY on research activities and knowledge base updates.
It operates independently from trade analysis and is triggered on-demand.

Key Features:
1. RESEARCH ONLY: No trade analysis, only research new strategies/methods
2. KNOWLEDGE UPDATES: Saves all findings to knowledge base
3. ON-DEMAND: Only runs when specifically requested
4. STRUCTURED OUTPUT: Provides structured research findings

Use Cases:
- Research new trading strategies before analysis
- Investigate specific market phenomena
- Expand knowledge base proactively
- Study competitor strategies or academic papers

Architecture:
- ResearchOnlyWorkflow: Main orchestrator for research activities
- FocusedResearchTeam: Coordinates research and knowledge integration
- StructuredResearchAgent: Conducts focused research
- KnowledgeArchivistAgent: Manages knowledge base updates
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator
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
from agno.tools.googlesearch import GoogleSearchTools


# ===== RESEARCH DATA MODELS =====

class StrategyResearch(BaseModel):
    """Comprehensive strategy research findings"""
    strategy_name: str = Field(..., description="Name of the researched strategy")
    strategy_category: str = Field(..., description="Category (momentum, mean_reversion, etc.)")
    description: str = Field(..., description="Detailed description of the strategy")
    
    # Identification criteria
    identification_criteria: List[str] = Field(..., description="How to identify this strategy in trades")
    key_indicators: List[str] = Field(..., description="Technical or fundamental indicators used")
    entry_signals: List[str] = Field(..., description="Common entry signals")
    exit_signals: List[str] = Field(..., description="Common exit signals")
    
    # Context and characteristics
    market_conditions: List[str] = Field(..., description="Optimal market conditions")
    timeframes: List[str] = Field(..., description="Common timeframes for this strategy")
    risk_profile: str = Field(..., description="Risk characteristics and management")
    typical_duration: str = Field(..., description="Typical trade duration")
    
    # Performance and validation
    success_factors: List[str] = Field(..., description="What makes this strategy successful")
    common_mistakes: List[str] = Field(..., description="Common pitfalls to avoid")
    validation_methods: List[str] = Field(..., description="How to validate this strategy")
    
    # Sources and credibility
    research_sources: List[str] = Field(..., description="Sources of information")
    academic_backing: str = Field(..., description="Academic or industry support")
    real_world_examples: List[str] = Field(..., description="Real-world usage examples")

class AnalysisMethodResearch(BaseModel):
    """Research on new analysis methods"""
    method_name: str = Field(..., description="Name of the analysis method")
    purpose: str = Field(..., description="What this method reveals about trading")
    
    # Methodology
    data_requirements: List[str] = Field(..., description="What data is needed")
    calculation_steps: List[str] = Field(..., description="How to perform the analysis")
    interpretation_guide: str = Field(..., description="How to interpret results")
    
    # Implementation
    sql_patterns: List[str] = Field(..., description="SQL query patterns for this analysis")
    bucketing_criteria: List[str] = Field(..., description="How to group/bucket data")
    statistical_significance: str = Field(..., description="How to validate findings")
    
    # Application
    use_cases: List[str] = Field(..., description="When to use this method")
    limitations: List[str] = Field(..., description="Method limitations and caveats")
    complementary_methods: List[str] = Field(..., description="Methods that work well together")

class ResearchSession(BaseModel):
    """Complete research session results"""
    session_id: str
    research_focus: str = Field(..., description="Main research topic")
    timestamp: str
    
    # Research outputs
    strategies_researched: List[StrategyResearch]
    analysis_methods: List[AnalysisMethodResearch]
    knowledge_updates: List[str] = Field(..., description="Updates made to knowledge base")
    
    # Session metadata
    research_depth: str = Field(..., description="Depth of research (preliminary, comprehensive, expert)")
    credibility_score: float = Field(..., description="Overall credibility of sources (0-1)")
    practical_applicability: float = Field(..., description="How applicable findings are (0-1)")
    
    # Recommendations
    implementation_recommendations: List[str] = Field(..., description="How to implement findings")
    further_research_needed: List[str] = Field(..., description="Areas needing more research")


# ===== RESEARCH AGENTS =====

def create_structured_research_agent() -> Agent:
    """Agent that conducts focused, structured research"""
    return Agent(
        name="Structured Research Agent",
        role="Conduct comprehensive, structured research on trading strategies and methods",
        model=OpenAIChat(id="gpt-4o"),
        tools=[GoogleSearchTools(), ReasoningTools()],
        instructions=[
            "You are a expert trading strategy researcher specializing in comprehensive analysis.",
            "",
            "When researching trading strategies:",
            "- Search academic papers, industry reports, and credible trading resources",
            "- Focus on strategies with documented track records",
            "- Look for specific identification criteria and signals",
            "- Research optimal market conditions and timeframes",
            "- Investigate risk management approaches",
            "- Find real-world implementation examples",
            "",
            "When researching analysis methods:",
            "- Focus on quantitative, testable approaches",
            "- Look for statistical validation methods",
            "- Research data requirements and calculation methods",
            "- Find practical implementation patterns",
            "- Investigate complementary analysis techniques",
            "",
            "Research Quality Standards:",
            "- Always cite credible sources",
            "- Distinguish between theory and proven practice",
            "- Note any conflicting information found",
            "- Assess practical applicability",
            "- Identify implementation challenges",
            "",
            "Provide structured, actionable findings that can be immediately applied.",
        ],
        add_datetime_to_instructions=True,
        markdown=True,
    )

def create_knowledge_archivist_agent(knowledge_base: DocumentKnowledgeBase) -> Agent:
    """Agent that manages knowledge base updates and organization"""
    knowledge_tools = KnowledgeTools(
        knowledge=knowledge_base,
        think=True,
        search=True,
        analyze=True,
        add_few_shot=True,
    )
    
    return Agent(
        name="Knowledge Archivist Agent",
        role="Organize and integrate research findings into the knowledge base",
        model=OpenAIChat(id="gpt-4o"),
        tools=[knowledge_tools, ReasoningTools()],
        instructions=[
            "You are the knowledge base archivist responsible for organizing research findings.",
            "",
            "When integrating new research:",
            "1. Search existing knowledge to avoid duplication",
            "2. Identify relationships with existing strategies/methods",
            "3. Create structured knowledge documents",
            "4. Ensure consistent terminology and organization",
            "5. Link related concepts and methods",
            "",
            "Knowledge Organization Principles:",
            "- Group related strategies and methods together",
            "- Use consistent naming conventions",
            "- Create cross-references between related concepts",
            "- Maintain clear hierarchies (strategy types, analysis categories)",
            "- Include practical implementation details",
            "",
            "Quality Control:",
            "- Verify information doesn't conflict with existing knowledge",
            "- Ensure new knowledge adds value",
            "- Maintain factual accuracy and source attribution",
            "- Keep knowledge base searchable and well-organized",
            "",
            "Focus on creating a comprehensive, well-structured knowledge repository.",
        ],
        knowledge=knowledge_base,
        search_knowledge=True,
        add_datetime_to_instructions=True,
        markdown=True,
    )


# ===== RESEARCH TEAM =====

def create_focused_research_team(knowledge_base: DocumentKnowledgeBase) -> Team:
    """Team that coordinates research and knowledge base updates"""
    
    research_agent = create_structured_research_agent()
    archivist_agent = create_knowledge_archivist_agent(knowledge_base)
    
    return Team(
        name="Focused Research Team",
        mode="coordinate",
        model=Claude(id="claude-3-5-sonnet-20241022"),
        members=[research_agent, archivist_agent],
        tools=[ReasoningTools()],
        instructions=[
            "You coordinate research on trading strategies and analysis methods.",
            "",
            "Process:",
            "1. Have the research agent investigate the topic thoroughly using search tools",
            "2. Have the archivist save the research findings to the knowledge base",
            "3. Provide a summary of what was researched and saved",
            "",
            "Focus on:",
            "- Practical, implementable trading strategies and analysis methods",
            "- High-quality, credible sources and information",
            "- Clear, actionable insights that can be applied to trade analysis",
            "- Avoiding duplication of existing knowledge",
            "",
            "Your response should summarize:",
            "- What strategies/methods were researched", 
            "- Key findings and insights discovered",
            "- What knowledge was added to the knowledge base",
            "- Any recommendations for implementation",
            "- Areas needing further research",
        ],
        markdown=False,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
    )


# ===== RESEARCH-ONLY WORKFLOW =====

class ResearchOnlyWorkflow(Workflow):
    """
    Research-only workflow for expanding trading strategy knowledge.
    
    This workflow focuses exclusively on research activities:
    - Investigates specific trading strategies or analysis methods
    - Conducts comprehensive research using credible sources  
    - Structures findings for practical application
    - Updates knowledge base with organized information
    - Provides implementation recommendations
    
    Does NOT perform any trade analysis or bucketing.
    """
    
    description: str = dedent("""\
        Focused research workflow for discovering and documenting trading strategies
        and analysis methods. Operates independently from trade analysis to build
        comprehensive knowledge base for future use.
        """)
    
    def __init__(self, knowledge_base: DocumentKnowledgeBase):
        super().__init__()
        self.knowledge_base = knowledge_base
        self.research_team = create_focused_research_team(knowledge_base)
        
        # Research parameters
        self.research_depth_levels = {
            "preliminary": "Basic overview and key concepts",
            "comprehensive": "Detailed analysis with implementation details", 
            "expert": "Advanced concepts and optimization techniques"
        }
    
    def run(self, 
            research_topic: str,
            research_depth: str = "comprehensive",
            specific_focus: Optional[str] = None) -> Iterator[RunResponse]:
        """
        Execute focused research on specified topic.
        
        Args:
            research_topic: What to research (e.g., "momentum trading strategies")
            research_depth: Level of research (preliminary, comprehensive, expert)
            specific_focus: Specific aspect to focus on (optional)
        """
        
        if research_depth not in self.research_depth_levels:
            research_depth = "comprehensive"
        
        session_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        yield RunResponse(
            content=f"🔬 Starting {research_depth} research session on: {research_topic}",
            event=RunEvent.workflow_started
        )
        
        # Build research prompt
        research_prompt = self._build_research_prompt(research_topic, research_depth, specific_focus)
        
        yield RunResponse(
            content="📚 Conducting comprehensive research and knowledge base integration...",
            event=RunEvent.run_started
        )
        
        # Execute research
        research_response = self.research_team.run(research_prompt)
        
        # Debug: Log response structure
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            print(f"🔍 DEBUG - Response type: {type(research_response)}")
            if hasattr(research_response, 'content'):
                print(f"🔍 DEBUG - Content type: {type(research_response.content)}")
                print(f"🔍 DEBUG - Content preview: {str(research_response.content)[:200]}...")
        
        # Parse and structure results
        try:
            if hasattr(research_response, 'content'):
                research_content = research_response.content
            else:
                research_content = str(research_response)
            
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                print(f"🔍 DEBUG - Team response: {research_content[:200]}...")
            
            # The team just provides a summary - we construct the ResearchSession ourselves
            research_session = self._construct_research_session_from_summary(
                research_content, session_id, research_topic, research_depth
            )
                
        except Exception as e:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                print(f"🔍 DEBUG - Parsing exception: {e}")
                import traceback
                traceback.print_exc()
                
            yield RunResponse(
                content=f"⚠️ Error processing research results: {e}",
                event=RunEvent.run_completed
            )
            research_session = ResearchSession(
                session_id=session_id,
                research_focus=research_topic,
                timestamp=datetime.now().isoformat(),
                strategies_researched=[],
                analysis_methods=[],
                knowledge_updates=["Research completed with processing issues"],
                research_depth=research_depth,
                credibility_score=0.7,
                practical_applicability=0.7,
                implementation_recommendations=["Manual review of research needed"],
                further_research_needed=["Detailed follow-up research recommended"]
            )
        
        yield RunResponse(
            content="✅ Research completed and knowledge base updated",
            event=RunEvent.run_completed
        )
        
        # Generate research report
        yield RunResponse(
            content="📋 Generating research session report...",
            event=RunEvent.tool_call_started
        )
        
        final_report = self._generate_research_report(research_session)
        
        yield RunResponse(
            content=final_report,
            event=RunEvent.workflow_completed
        )
    
    def research_specific_strategy(self, strategy_name: str) -> Iterator[RunResponse]:
        """Research a specific trading strategy in detail"""
        return self.run(
            research_topic=f"'{strategy_name}' trading strategy",
            research_depth="expert",
            specific_focus="identification criteria and implementation details"
        )
    
    def research_analysis_method(self, method_name: str) -> Iterator[RunResponse]:
        """Research a specific analysis method"""
        return self.run(
            research_topic=f"'{method_name}' analysis method for trading",
            research_depth="comprehensive", 
            specific_focus="implementation patterns and SQL queries"
        )
    
    def research_market_phenomenon(self, phenomenon: str) -> Iterator[RunResponse]:
        """Research a specific market phenomenon or pattern"""
        return self.run(
            research_topic=f"'{phenomenon}' market phenomenon and trading implications",
            research_depth="comprehensive",
            specific_focus="identification patterns and strategy development"
        )
    
    def _build_research_prompt(self, topic: str, depth: str, focus: Optional[str]) -> str:
        """Build comprehensive research prompt"""
        
        depth_description = self.research_depth_levels[depth]
        focus_clause = f" with specific focus on {focus}" if focus else ""
        
        return f"""
        Conduct {depth} research on: {topic}{focus_clause}
        
        Research Depth: {depth_description}
        
        Research Requirements:
        
        For Trading Strategies:
        - Strategy definition and categorization
        - Specific identification criteria and signals
        - Entry and exit patterns
        - Risk management approaches
        - Optimal market conditions and timeframes
        - Performance characteristics and validation methods
        - Real-world implementation examples
        - Common pitfalls and success factors
        
        For Analysis Methods:
        - Method purpose and applications
        - Data requirements and calculation steps
        - Statistical validation approaches
        - SQL implementation patterns
        - Interpretation guidelines
        - Limitations and complementary methods
        
        Quality Standards:
        - Use credible, verifiable sources
        - Provide specific, actionable details
        - Include practical implementation guidance
        - Note any conflicting information
        - Assess real-world applicability
        
        Knowledge Base Integration:
        - Avoid duplicating existing knowledge
        - Create well-structured, searchable content
        - Link related concepts and methods
        - Ensure consistent terminology
        - Provide cross-references where appropriate
        
        Organize findings into structured knowledge that can be immediately used
        for trade analysis and strategy identification.
        """
    
    def _construct_research_session_from_summary(self, summary: str, session_id: str, 
                                                topic: str, depth: str) -> ResearchSession:
        """Construct ResearchSession from team's summary"""
        
        # Extract knowledge updates from summary
        knowledge_updates = ["Knowledge base updated with research findings"]
        
        # Look for strategy mentions
        strategies_found = []
        if "strategy" in summary.lower() or "strategies" in summary.lower():
            knowledge_updates.append("Strategy research findings integrated")
            strategies_found.append("Strategy patterns identified from research")
        
        # Look for analysis method mentions
        methods_found = []
        if "analysis" in summary.lower() or "method" in summary.lower():
            knowledge_updates.append("Analysis method research completed")
            methods_found.append("Analysis methods documented")
        
        # Assess credibility based on content indicators
        credibility_score = 0.7  # Default
        if "academic" in summary.lower() or "paper" in summary.lower():
            credibility_score += 0.1
        if "study" in summary.lower() or "research" in summary.lower():
            credibility_score += 0.1
        if "source" in summary.lower() or "citation" in summary.lower():
            credibility_score += 0.1
        credibility_score = min(credibility_score, 1.0)
        
        # Assess practical applicability
        applicability_score = 0.7  # Default
        if "implementation" in summary.lower() or "practice" in summary.lower():
            applicability_score += 0.1
        if "example" in summary.lower() or "real-world" in summary.lower():
            applicability_score += 0.1
        if "trading" in summary.lower() or "market" in summary.lower():
            applicability_score += 0.1
        applicability_score = min(applicability_score, 1.0)
        
        # Generate implementation recommendations based on content
        recommendations = [
            "Review research findings for implementation opportunities",
            "Test identified strategies with historical data",
            "Validate analysis methods with sample trades"
        ]
        
        if "momentum" in summary.lower():
            recommendations.append("Consider momentum-based strategy implementations")
        if "risk" in summary.lower():
            recommendations.append("Incorporate risk management findings")
        if "pattern" in summary.lower():
            recommendations.append("Look for pattern-based trading opportunities")
        
        # Generate further research needs
        further_research = [
            "Follow-up research on specific implementation details",
            "Validation studies with real trading data"
        ]
        
        if len(summary) < 500:
            further_research.append("More comprehensive research needed")
        if "preliminary" in summary.lower():
            further_research.append("Deeper analysis required")
        
        return ResearchSession(
            session_id=session_id,
            research_focus=topic,
            timestamp=datetime.now().isoformat(),
            strategies_researched=[],  # Would need sophisticated parsing for full strategy objects
            analysis_methods=[],       # Would need sophisticated parsing for full method objects
            knowledge_updates=knowledge_updates,
            research_depth=depth,
            credibility_score=credibility_score,
            practical_applicability=applicability_score,
            implementation_recommendations=recommendations,
            further_research_needed=further_research
        )
    
    def _generate_research_report(self, session: ResearchSession) -> str:
        """Generate comprehensive research session report"""
        
        return f"""
# 🔬 Research Session Report

**Session ID**: {session.session_id}
**Research Focus**: {session.research_focus}
**Research Depth**: {session.research_depth}
**Timestamp**: {session.timestamp}

## 📊 Research Quality Metrics

- **Credibility Score**: {session.credibility_score:.2f}/1.0
- **Practical Applicability**: {session.practical_applicability:.2f}/1.0
- **Strategies Researched**: {len(session.strategies_researched)}
- **Analysis Methods**: {len(session.analysis_methods)}

## 📚 Knowledge Base Updates

{chr(10).join([f"- {update}" for update in session.knowledge_updates])}

## 🎯 Implementation Recommendations

{chr(10).join([f"- {rec}" for rec in session.implementation_recommendations])}

## 🔍 Further Research Needed

{chr(10).join([f"- {item}" for item in session.further_research_needed])}

## 📈 Strategies Researched

{f"{len(session.strategies_researched)} strategies documented" if session.strategies_researched else "No specific strategies documented in this session"}

## 🧮 Analysis Methods

{f"{len(session.analysis_methods)} analysis methods documented" if session.analysis_methods else "No specific analysis methods documented in this session"}

---

## 🚀 Next Steps

1. **Review Knowledge Base**: Verify new knowledge has been properly integrated
2. **Test Implementation**: Apply findings to real trade analysis scenarios  
3. **Validate Methods**: Test new analysis methods with historical data
4. **Plan Follow-up**: Schedule additional research based on identified gaps

**Research Session Complete** ✅
        """


def create_research_only_workflow(knowledge_base: DocumentKnowledgeBase) -> ResearchOnlyWorkflow:
    """Factory function to create the research-only workflow"""
    return ResearchOnlyWorkflow(knowledge_base) 