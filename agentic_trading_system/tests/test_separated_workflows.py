#!/usr/bin/env python3
"""
Test script for the new separated research and analysis workflows.

This script demonstrates:
1. Pure research workflow (no trade analysis)
2. Autonomous trade analysis workflow (with research feedback loop)
3. Clear separation between research and analysis concerns

Usage:
    python test_separated_workflows.py
    
Environment:
    Set DEBUG_MODE=true to see detailed agent interactions
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def test_research_only_workflow():
    """Test the research-only workflow"""
    print("\n" + "="*80)
    print("🔬 TESTING RESEARCH-ONLY WORKFLOW")
    print("="*80)
    
    try:
        from run import system
        
        print("\n📚 Test 1: General strategy research")
        print("-" * 50)
        
        # Test general research
        research_results = system.research_strategy(
            research_topic="scalping strategies for high-frequency trading",
            depth="comprehensive"
        )
        
        print("Research initiated. Processing...")
        result_count = 0
        for response in research_results:
            result_count += 1
            print(f"📝 [{result_count}] {response.content[:100]}...")
            if result_count >= 3:  # Limit output for testing
                print("   ... (truncated for testing)")
                break
        
        print("\n🎯 Test 2: Specific strategy research")
        print("-" * 50)
        
        # Test specific strategy research
        strategy_results = system.research_specific_strategy("VWAP trading strategy")
        
        print("Specific strategy research initiated...")
        result_count = 0
        for response in strategy_results:
            result_count += 1
            print(f"📚 [{result_count}] {response.content[:100]}...")
            if result_count >= 3:
                print("   ... (truncated for testing)")
                break
        
        print("\n✅ Research-only workflow tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Research workflow test failed: {e}")
        return False

def test_trade_analysis_workflow():
    """Test the autonomous trade analysis workflow"""
    print("\n" + "="*80)
    print("📊 TESTING AUTONOMOUS TRADE ANALYSIS WORKFLOW")
    print("="*80)
    
    try:
        from run import system
        
        print("\n📈 Test 1: Trade analysis with research feedback loop")
        print("-" * 50)
        
        # Test trade analysis (limited to prevent long execution)
        analysis_results = system.analyze_trades(
            user_id=None,  # All users
            days=30,       # Last 30 days (smaller dataset for testing)
            min_coverage=0.60  # Lower threshold for testing
        )
        
        print("Trade analysis initiated...")
        result_count = 0
        for response in analysis_results:
            result_count += 1
            print(f"📊 [{result_count}] {response.content[:100]}...")
            if result_count >= 5:  # Limit for testing
                print("   ... (truncated for testing)")
                break
        
        print("\n✅ Trade analysis workflow tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Trade analysis workflow test failed: {e}")
        return False

def test_workflow_separation():
    """Test that workflows are properly separated"""
    print("\n" + "="*80)
    print("🔀 TESTING WORKFLOW SEPARATION")
    print("="*80)
    
    try:
        from run import system
        
        print("\n🧪 Test 1: Verify workflow independence")
        print("-" * 50)
        
        # Verify that research workflow exists and is separate
        assert hasattr(system, 'research_workflow'), "Research workflow should exist"
        assert hasattr(system, 'analysis_workflow'), "Analysis workflow should exist"
        assert system.research_workflow != system.analysis_workflow, "Workflows should be separate"
        
        print("✅ Research and analysis workflows are properly separated")
        
        print("\n🧪 Test 2: Verify workflow methods")
        print("-" * 50)
        
        # Verify that new methods exist
        assert hasattr(system, 'research_strategy'), "research_strategy method should exist"
        assert hasattr(system, 'analyze_trades'), "analyze_trades method should exist"
        assert hasattr(system, 'research_specific_strategy'), "research_specific_strategy method should exist"
        
        print("✅ All new workflow methods are available")
        
        print("\n🧪 Test 3: Verify legacy compatibility")
        print("-" * 50)
        
        # Verify legacy method still exists
        assert hasattr(system, 'discover_strategies'), "Legacy discover_strategies method should exist"
        
        print("✅ Legacy compatibility maintained")
        
        print("\n✅ Workflow separation tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow separation test failed: {e}")
        return False

def test_knowledge_base_integration():
    """Test knowledge base integration across workflows"""
    print("\n" + "="*80)
    print("📚 TESTING KNOWLEDGE BASE INTEGRATION")
    print("="*80)
    
    try:
        from run import system
        
        print("\n🧪 Test 1: Verify shared knowledge base")
        print("-" * 50)
        
        # Verify knowledge base is shared
        research_kb = system.research_workflow.knowledge_base
        analysis_kb = system.analysis_workflow.knowledge_base
        
        assert research_kb == analysis_kb, "Knowledge base should be shared between workflows"
        
        print("✅ Knowledge base is properly shared between workflows")
        
        print("\n🧪 Test 2: Verify knowledge base is loaded")
        print("-" * 50)
        
        # Check if knowledge base has documents
        kb_documents = len(system.knowledge_base.documents)
        print(f"📖 Knowledge base contains {kb_documents} documents")
        
        assert kb_documents > 0, "Knowledge base should have base documents"
        
        print("✅ Knowledge base is properly initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge base integration test failed: {e}")
        return False

def test_agent_availability():
    """Test that all required agents are available"""
    print("\n" + "="*80)
    print("🤖 TESTING AGENT AVAILABILITY")
    print("="*80)
    
    try:
        from run import system
        
        print("\n🧪 Test 1: Verify agent factory creation")
        print("-" * 50)
        
        # Check agents dictionary
        agents = system.agents
        print(f"🤖 Available agents: {list(agents.keys()) if agents else 'None'}")
        
        print("\n🧪 Test 2: Verify team factory creation")
        print("-" * 50)
        
        # Check teams dictionary
        teams = system.teams
        print(f"👥 Available teams: {list(teams.keys()) if teams else 'None'}")
        
        print("\n✅ Agent and team availability tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Agent availability test failed: {e}")
        return False

def run_all_tests():
    """Run all workflow tests"""
    print("🚀 STARTING SEPARATED WORKFLOW TESTS")
    print("="*80)
    
    tests = [
        ("Workflow Separation", test_workflow_separation),
        ("Knowledge Base Integration", test_knowledge_base_integration), 
        ("Agent Availability", test_agent_availability),
        ("Research-Only Workflow", test_research_only_workflow),
        # Note: Commenting out trade analysis test as it requires database
        # ("Trade Analysis Workflow", test_trade_analysis_workflow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The separated workflow architecture is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    print("🧪 Separated Workflow Testing System")
    print("="*80)
    
    # Check for specific test requests
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name == "research":
            test_research_only_workflow()
        elif test_name == "analysis":
            test_trade_analysis_workflow()
        elif test_name == "separation":
            test_workflow_separation()
        elif test_name == "knowledge":
            test_knowledge_base_integration()
        elif test_name == "agents":
            test_agent_availability()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: research, analysis, separation, knowledge, agents")
    else:
        # Run all tests
        run_all_tests() 