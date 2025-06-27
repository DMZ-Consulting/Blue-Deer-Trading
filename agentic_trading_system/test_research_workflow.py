#!/usr/bin/env python3
"""
Simple test script for the research workflow to validate JSON parsing improvements.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def test_research_workflow_simple():
    """Simple test of research workflow with improved parsing"""
    print("🔬 Testing Research Workflow with Improved JSON Parsing")
    print("="*60)
    
    try:
        from run import system
        
        # Enable debug mode to see response structure
        os.environ['DEBUG_MODE'] = 'true'
        
        print("📚 Testing simple strategy research...")
        
        # Test with a simple, focused research topic
        research_results = system.research_strategy(
            research_topic="simple moving average crossover strategy",
            depth="preliminary"  # Use preliminary for faster testing
        )
        
        print("\n📝 Research Results:")
        result_count = 0
        for response in research_results:
            result_count += 1
            print(f"[{result_count}] {response.content[:150]}{'...' if len(response.content) > 150 else ''}")
            
            # Stop after a few responses for testing
            #if result_count >= 5:
           #     print("   ... (stopping for test)")
           #     break
        
        print("\n✅ Research workflow test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Research workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parsing_only():
    """Test just the parsing logic without running the full workflow"""
    print("\n🧪 Testing JSON Parsing Logic")
    print("="*40)
    
    try:
        from workflows.research_only import ResearchOnlyWorkflow
        from utils.knowledge_manager import create_base_knowledge_documents
        from agno.knowledge.document import DocumentKnowledgeBase
        from agno.vectordb.lancedb import LanceDb, SearchType
        from agno.embedder.openai import OpenAIEmbedder
        
        # Create minimal knowledge base
        documents = create_base_knowledge_documents()
        knowledge_base = DocumentKnowledgeBase(
            documents=documents,
            vector_db=LanceDb(
                table_name="test_parsing",
                uri="./tmp/test_parsing_lancedb",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        )
        knowledge_base.load(recreate=False)
        
        # Create workflow
        workflow = ResearchOnlyWorkflow(knowledge_base)
        
        # Test text parsing
        session_id = "test_session"
        topic = "test topic"
        depth = "preliminary"
        
        sample_text = """
        This is a research response about momentum trading strategies.
        The research shows that momentum strategies work well in trending markets.
        Academic studies support the use of moving averages for trend detection.
        Implementation requires careful risk management and position sizing.
        """
        
        parsed_session = workflow._parse_research_response(sample_text, session_id, topic, depth)
        
        print(f"✅ Parsed session ID: {parsed_session.session_id}")
        print(f"✅ Research focus: {parsed_session.research_focus}")
        print(f"✅ Credibility score: {parsed_session.credibility_score}")
        print(f"✅ Knowledge updates: {len(parsed_session.knowledge_updates)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Research Workflow Testing")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "parsing":
        # Test just the parsing logic
        test_parsing_only()
    else:
        # Test the full workflow
        print("Running full workflow test...")
        print("(Use 'python test_research_workflow.py parsing' to test just parsing)")
        print()
        
        success = test_research_workflow_simple()
        
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️ Some tests failed - check output above") 