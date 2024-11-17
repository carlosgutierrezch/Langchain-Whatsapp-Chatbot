
from app.services.SQLAgent import SQLAgent
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/main/Desktop/chatbot/bot/lib/python3.13/site-packages')))
from langgraph.graph import END, START, StateGraph, MessagesState
from app.services.State import InputState, OutputState
class Workflow:
    def __init__(self):
        self.sql_agent = SQLAgent()

    def create_workflow(self) -> StateGraph:
        """Create and configure the workflow graph."""
        workflow = StateGraph(input=InputState, output=OutputState)

        # Add nodes to the graph
        workflow.add_node("parse_question", self.sql_agent.parse_question)
        workflow.add_node("generate_sql", self.sql_agent.generate_sql)
        workflow.add_node("validate_and_fix_sql", self.sql_agent.validate_and_fix_sql)
        workflow.add_node("execute_sql", self.sql_agent.execute_sql)
        workflow.add_node("format_results", self.sql_agent.format_results)
        workflow.add_node("choose_recommendation", self.sql_agent.choose_recommendation)
        
        # Define edges
        workflow.add_edge("parse_question", "generate_sql")
        workflow.add_edge("generate_sql", "validate_and_fix_sql")
        workflow.add_edge("validate_and_fix_sql", "execute_sql")
        workflow.add_edge("execute_sql", "format_results")
        workflow.add_edge("format_results", "choose_recommendation")
        workflow.add_edge("choose_recommendation", END)
        workflow.set_entry_point("parse_question")

        return workflow
    
    def returnGraph(self):
        return self.workflow

    def run_sql_agent(self, question: str, uuid: str) -> dict:
        """Run the SQL agent workflow and return the formatted answer and recommendation."""
        app = self.create_workflow().compile()
        result = app.invoke({"question": question, "uuid": uuid})
        return {
            "answer": result['answer'],
            "recommendation": result['recommendation'],
            "recommendation_reason": result['recommendation_reason'],
            "formatted_data_for_recommendation": result['formatted_data_for_recommendation']
        }
        
# from State import InputState, OutputState
# from SQLAgent import SQLAgent
# from langgraph.graph import END, START, StateGraph

# class WorkflowManager:
#     def __init__(self):
#         self.sql_agent = SQLAgent()
#         self.workflow = self.create_workflow().compile()

#     def create_workflow(self) -> StateGraph:
#         """Create and configure the workflow graph."""
#         workflow = StateGraph(input=InputState, output=OutputState)

#         # Add nodes to the graph
#         workflow.add_node("parse_question", self.sql_agent.parse_question)
#         workflow.add_node("generate_sql", self.sql_agent.generate_sql)
#         workflow.add_node("validate_and_fix_sql", self.sql_agent.validate_and_fix_sql)
#         workflow.add_node("execute_sql", self.sql_agent.execute_sql)
#         workflow.add_node("format_results", self.sql_agent.format_results)
#         workflow.add_node("choose_recommendation", self.sql_agent.choose_recommendation)
        
#         # Define edges
#         workflow.add_edge("parse_question", "get_unique_nouns")
#         workflow.add_edge("get_unique_nouns", "generate_sql")
#         workflow.add_edge("generate_sql", "validate_and_fix_sql")
#         workflow.add_edge("validate_and_fix_sql", "execute_sql")
#         workflow.add_edge("execute_sql", "format_results")
#         workflow.add_edge("execute_sql", "choose_recommendation")
#         workflow.add_edge("choose_recommendation", "format_data_for_recommendation")
#         workflow.add_edge("format_data_for_recommendation", END)
#         workflow.set_entry_point("parse_question")

#         return workflow
    
#     def returnGraph(self):
#         """Return the compiled workflow."""
#         return self.workflow

#     def run_sql_agent(self, question: str, uuid: str) -> dict:
#         """Run the SQL agent workflow and return the formatted answer and recommendation."""
#         try:
#             result = self.workflow.invoke({"question": question, "uuid": uuid})
#             return {
#                 "answer": result.get('answer', 'No answer found'),
#                 "recommendation": result.get('recommendation', 'No recommendation found'),
#                 "recommendation_reason": result.get('recommendation_reason', 'No reason found'),
#                 "formatted_data_for_recommendation": result.get('formatted_data_for_recommendation', 'No data found')
#             }
#         except Exception as e:
#             # Log the error and provide fallback response
#             logging.error(f"Error while running SQL agent: {e}")
#             return {"error": "An error occurred while processing the request."}