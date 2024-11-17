
from app.services.SQLAgent import SQLAgent
from app.services.State import InputState, OutputState
from langgraph.graph import END, START, StateGraph
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/main/Desktop/chatbot/bot/lib/python3.13/site-packages')))

        
class Workflow:
    def __init__(self):
        self.sql_agent = SQLAgent()

    def create_workflow(self) -> StateGraph:
        """Create and configure the workflow graph."""
        workflow = StateGraph(input=InputState, output=OutputState)

        # Add nodes to the graph
        workflow.add_node("parse_question", self.sql_agent.parse_question)
        workflow.add_node("get_unique_nouns", self.sql_agent.get_unique_nouns)
        workflow.add_node("generate_sql", self.sql_agent.generate_sql)
        workflow.add_node("validate_and_fix_sql", self.sql_agent.validate_and_fix_sql)
        workflow.add_node("execute_sql", self.sql_agent.execute_sql)
        workflow.add_node("format_results", self.sql_agent.format_results)
        workflow.add_node("choose_recommendation", self.sql_agent.choose_recommendation)
        
        # Define edges
        workflow.add_edge("parse_question", "get_unique_nouns")
        workflow.add_edge("get_unique_nouns", "generate_sql")
        workflow.add_edge("generate_sql", "validate_and_fix_sql")
        workflow.add_edge("validate_and_fix_sql", "execute_sql")
        workflow.add_edge("execute_sql", "format_results")
        workflow.add_edge("execute_sql", "choose_recommendation")
        workflow.add_edge("choose_recommendation", END)
        workflow.add_edge("format_results", END)
        workflow.set_entry_point("parse_question")

        return workflow
    
    def returnGraph(self):
        return self.create_workflow().compile()

    def run_sql_agent(self, question: str, uuid: str) -> dict:
        """Run the SQL agent workflow and return the formatted answer and visualization recommendation."""
        app = self.create_workflow().compile()
        result = app.invoke({"question": question, "uuid": uuid})
        return {
            "answer": result['answer'],
            "recommendation": result['recommendation'],
            "recommendation_reason": result['recommendation_reason']
        }
        
# class Workflow:
#     def __init__(self):
#         self.sql_agent = SQLAgent()

#     def create_workflow(self) -> StateGraph:
#         """Create and configure the workflow graph."""
#         workflow = StateGraph(input=InputState, output=OutputState)

#         # Add nodes to the graph
#         workflow.add_node("is_greeting", self.sql_agent.is_greeting)
#         workflow.add_node("detect_language", self.sql_agent.detect_language)
#         workflow.add_node("is_restaurant_query", self.sql_agent.is_restaurant_query)
#         workflow.add_node("process_message", self.sql_agent.process_message)
#         workflow.add_node("get_casual_response", self.sql_agent.get_casual_response)
#         workflow.add_node("process_restaurant_query", self.sql_agent.process_restaurant_query)
#         workflow.add_node("generate_and_execute_sql", self.sql_agent.generate_and_execute_sql)
#         workflow.add_node("format_recommendation", self.sql_agent.format_recommendation)
#         workflow.add_node("get_no_results_response", self.sql_agent.get_no_results_response)
#         workflow.add_node("extract_urls", self.sql_agent.extract_urls)
    
#         # Define edges
#         workflow.add_edge("is_greeting", "detect_language")
#         workflow.add_edge("detect_language", "is_restaurant_query")
#         workflow.add_edge("is_restaurant_query", "process_message")
#         workflow.add_edge("process_message", "get_casual_response")
#         workflow.add_edge("get_casual_response", "process_restaurant_query")
#         workflow.add_edge("process_restaurant_query", "generate_and_execute_sql")
#         workflow.add_edge("generate_and_execute_sql", "format_recommendation")
#         workflow.add_edge("format_recommendation", "get_no_results_response")
#         workflow.add_edge("get_no_results_response", "extract_urls")
#         workflow.add_edge("extract_urls", END)

#         # Define entry point
#         workflow.set_entry_point("is_greeting")

#         return workflow

#     def returnGraph(self):
#         """Return the workflow graph."""
#         return self.create_workflow()

#     def run_sql_agent(self, question: str, uuid: str) -> dict:
#         """Run the SQL agent workflow and return the formatted answer and recommendation."""
#         try:
#             app = self.create_workflow().compile()
#             result = app.invoke({"question": question, "uuid": uuid})
#             return {
#                 "answer": result.get('answer', None),
#                 "recommendation": result.get('recommendation', None),
#                 "recommendation_reason": result.get('recommendation_reason', None),
#                 "formatted_data_for_recommendation": result.get('formatted_data_for_recommendation', None)
#             }
#         except Exception as e:
#             logging.error(f"Error while running SQL agent: {e}")
#             return {"error": "An error occurred while processing the request."}
        