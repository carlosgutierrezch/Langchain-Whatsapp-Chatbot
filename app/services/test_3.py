from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from DatabaseManager import DatabaseManager
from LLMManager import LLMManager
from SQLAgent import SQLAgent

def test_sql_agent_workflow():
    # Initialize DatabaseManager and LLMManager
    db_manager = DatabaseManager(db_path="all_data.db")
    llm_manager = LLMManager()

    # Initialize SQLAgent with real DatabaseManager and LLMManager
    sql_agent = SQLAgent()
    sql_agent.db_manager = db_manager
    sql_agent.llm_manager = llm_manager

    # Example question to test the complete workflow
    state = {'question': 'What are the top-rated restaurants?'}
    
    # Step 1: Parse the question
    parsed_question = sql_agent.parse_question(state)
    print("Parsed Question Output:", parsed_question)

    # Store parsed question in state
    state['parsed_question'] = parsed_question['parsed_question']

    # Step 2: Get unique nouns
    unique_nouns = sql_agent.get_unique_nouns(state)
    print("Unique Nouns:", unique_nouns)

    # Store unique nouns in state
    state['unique_nouns'] = unique_nouns['unique_nouns']

    # Step 3: Generate SQL query
    generated_sql = sql_agent.generate_sql(state)
    print("Generated SQL Query:", generated_sql)

    # Check if SQL query was generated
    if 'sql_query' not in generated_sql or generated_sql['sql_query'] == "NOT_RELEVANT":
        print("SQL Query could not be generated. Exiting workflow.")
        return

    # Store generated SQL query in state
    state['sql_query'] = generated_sql['sql_query']

    # Step 4: Validate and fix the SQL query
    validated_sql = sql_agent.validate_and_fix_sql(state)
    print("Validated SQL Query:", validated_sql)

    # Step 5: Execute the SQL query
    state['sql_query'] = validated_sql['sql_query']
    execution_results = sql_agent.execute_sql(state)
    print("Execution Results:", execution_results)

    # Step 6: Format results into a human-readable response
    state['results'] = execution_results['results']
    formatted_results = sql_agent.format_results(state)
    print("Formatted Results:", formatted_results)

    # Step 7: Choose a recommendation based on results
    recommendation = sql_agent.choose_recommendation(state)
    print("Recommendation:", recommendation)

if __name__ == "__main__":
    test_sql_agent_workflow()