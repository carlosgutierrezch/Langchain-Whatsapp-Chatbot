from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.services.DatabaseManager import DatabaseManager
from app.services.LLMManager import LLMManager
import re

class SQLAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_manager = LLMManager()
        
        # Define common greetings in multiple languages
        self.greeting_patterns = {
            'english': r'\b(hi|hello|hey|good morning|good afternoon|good evening|greetings)\b',
            'spanish': r'\b(hola|buenos días|buenas tardes|buenas noches)\b',
        }
    def is_greeting(self, text: str) -> bool:
        """Check if the input is a casual greeting."""
        text = text.lower().strip()
        for patterns in self.greeting_patterns.values():
            if re.search(patterns, text, re.IGNORECASE):
                return True
        return False
    
    def get_casual_response(self, text: str) -> dict:
     """Generate a casual, friendly response for greetings."""
     prompt = ChatPromptTemplate.from_messages([
         ("system", '''You are a friendly, laid-back AI assistant who enjoys casual conversations. When users greet you, respond with a warm, informal tone in their language (Spanish or English). Keep it light and relaxed, and mention that you're happy to help with restaurant suggestions, but only if needed. 
         If the user greets in Spanish, respond in Spanish. If in English, respond in English.'''),
         ("human", "{text}")
     ])
     
     response = self.llm_manager.invoke(prompt, text=text)
     
     return {
         "answer": response,
         "recommendation": "No recommendation",
         "recommendation_reason": "Casual conversation",
         "formatted_data_for_recommendation": {}
     }

    def parse_question(self, state: dict) -> dict:
        """Parse user question and identify relevant tables and columns."""
        question = state['question']
        
        # Check if it's a casual greeting first
        if self.is_greeting(question):
            return {
                "parsed_question": {
                    "is_relevant": False,
                    "message": "GREETING",
                    "relevant_tables": []
                }
            }

        # Obtain the database schema
        schema = self.db_manager.get_schema()

        # Construct the prompt to identify if the question is related to the restaurants database
        prompt = ChatPromptTemplate.from_messages([
            ("system", '''You are an AI assistant for a restaurant recommendation service in Madrid. 
            Based on the user's question, check if it's related to restaurants or a general inquiry. 
            Use the provided database schema to identify relevant tables and columns for the query. 
            Only proceed with querying the database if the question is relevant to restaurant recommendations. Otherwise, respond casually.'''),
            ("human", f"===User question:\n{question}\n\n===Database schema:\n{schema}\n\nIs this question relevant to the restaurant database? If yes, identify the relevant tables and columns.")
        ])

        # Invoke the model
        response = self.llm_manager.invoke(prompt, question=question, schema=schema)
        
        # Parse the model's response (this should now give us a structured answer)
        output_parser = JsonOutputParser()  # You can adjust the parser based on the output format
        parsed_response = output_parser.parse(response)

        # If the question is not relevant, we indicate that and provide a casual response
        if not parsed_response.get("is_relevant", True):
            parsed_response["is_relevant"] = False
            parsed_response["message"] = "This seems like a general question. Feel free to ask about restaurants in Madrid!"
        
        return {"parsed_question": parsed_response}

    def generate_sql(self, state: dict) -> dict:
        """Generate SQL query based on parsed question."""
        question = state['question']
        parsed_question = state['parsed_question']

        if not parsed_question['is_relevant']:
            return {"sql_query": "NOT_RELEVANT", "is_relevant": False}
    
        schema = self.db_manager.get_schema(state['uuid'])

        prompt = ChatPromptTemplate.from_messages([
            ("system", '''
                You are an AI assistant that generates SQL queries to answer questions about restaurants in Madrid. Based on the user’s question, use the relevant tables and columns from the database schema to construct a valid SQL query.
                
                If there is insufficient information to construct a SQL query, respond with "NOT_ENOUGH_INFO".
                For responses requiring charts, such as a distribution of ratings or prices:
                - Use the format `[[x, y]]` or `[[label, x, y]]` for results.
                - "x" should represent the rating, price, or relevant metric; "y" should represent the count or frequency.
                - Exclude rows where any column contains NULL, "N/A," or an empty string.

                SKIP ALL ROWS WHERE ANY COLUMN IS NULL or "N/A" or "".
                Provide only the query string. Ensure that table and column names are enclosed in backticks, and use exact spellings from the unique nouns list provided.
                '''),
                ("human", '''===Database schema:
                {schema}

                ===User question:
                {question}

                ===Relevant tables and columns:
                {parsed_question}

                ===Unique nouns in relevant tables:
                {unique_nouns}

                Generate SQL query string'''),
        ])

        response = self.llm_manager.invoke(prompt, schema=schema, question=question, parsed_question=parsed_question, unique_nouns=unique_nouns)
        
        if response.strip() == "NOT_ENOUGH_INFO":
            return {"sql_query": "NOT_RELEVANT"}
        else:
            return {"sql_query": response}

    def validate_and_fix_sql(self, state: dict) -> dict:
        """Validate and fix the generated SQL query."""
        sql_query = state['sql_query']

        if sql_query == "NOT_RELEVANT":
            return {"sql_query": "NOT_RELEVANT", "sql_valid": False}
        
        schema = self.db_manager.get_schema(state['uuid'])

        prompt = ChatPromptTemplate.from_messages([
            ("system", '''
                You are an AI assistant that validates and fixes SQL queries. Your task is to:
                1. Check if the SQL query is valid.
                2. Ensure all table and column names are correctly spelled and exist in the schema. All the table and column names should be enclosed in backticks.
                3. If there are any issues, fix them and provide the corrected SQL query.
                4. If no issues are found, return the original query.

                Respond in JSON format with the following structure. Only respond with the JSON:
                {{
                    "valid": boolean,
                    "issues": string or null,
                    "corrected_query": string
                }}
            '''),
            ("human", '''===Database schema:
            {schema}

            ===Generated SQL query:
            {sql_query}

            Respond in JSON format with the following structure. Only respond with the JSON:
            {{
                "valid": boolean,
                "issues": string or null,
                "corrected_query": string
            }}
            '''), 
        ])

        output_parser = JsonOutputParser()
        response = self.llm_manager.invoke(prompt, schema=schema, sql_query=sql_query)
        result = output_parser.parse(response)

        if result["valid"] and result["issues"] is None:
            return {"sql_query": sql_query, "sql_valid": True}
        else:
            return {
                "sql_query": result["corrected_query"],
                "sql_valid": result["valid"],
                "sql_issues": result["issues"]
            }

    def execute_sql(self, state: dict) -> dict:
        """Execute SQL query and return results."""
        query = state['sql_query']
        uuid = state['uuid']
        
        if query == "NOT_RELEVANT":
            return {"results": "NOT_RELEVANT"}

        try:
            results = self.db_manager.execute_query(uuid, query)
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    def format_results(self, state: dict) -> dict:
        """Format query results into a human-readable response."""
        question = state['question']
        results = state['results']

        # Handle greetings
        if (state.get('parsed_question', {}).get('message') == "GREETING"):
            return self.get_casual_response(question)

        if results == "NOT_RELEVANT":
            return {
                "answer": "I can help you find restaurants in Madrid! Feel free to ask me about restaurants, cuisines, ratings, or specific areas.",
                "recommendation": "No recommendation",
                "recommendation_reason": "General conversation",
                "formatted_data_for_recommendation": {}
            }

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that formats database query results into a human-readable response. Give a conclusion to the user's question based on the query results. Do not give the answer in markdown format. Only give the answer in one line."),
            ("human", "User question: {question}\n\nQuery results: {results}\n\nFormatted response:"),
        ])

        response = self.llm_manager.invoke(prompt, question=question, results=results)
        return {"answer": response}


    def choose_recommendation(self, state: dict) -> dict:
        """Choose an appropriate recommendation from the data."""
        question = state['question']
        results = state['results']
        sql_query = state['sql_query']

        if results == "NOT_RELEVANT":
            return {
                "recommendation": "No recommendation",
                "recommendation_reason": "No visualization needed.",
                "formatted_data_for_recommendation": {}  # Return empty dictionary
            }

        prompt = ChatPromptTemplate.from_messages([
            ("system", '''
            You are an AI assistant that recommends restaurants located in the city of Madrid. Based on the user's question, SQL query, and query results, suggest the most suitable restaurant from the data. If no recommendation is appropriate, indicate that.

        - If the user asks about a specific restaurant, provide the URL for that restaurant.
            - For each of the top 5 restaurants, provide the description in plain text.

            Provide your response in the following format:

            User question: {question}
            Neighborhood: [Neighborhood name]
            Top 5 Restaurants:
            1. [Restaurant name]
            URL: [Restaurant URL]
            Description: [Restaurant description in plain text]
            2. [Restaurant name] 
            URL: [Restaurant URL]
            Description: [Restaurant description in plain text]
            3. [Restaurant name]
            URL: [Restaurant URL] 
            Description: [Restaurant description in plain text]
            4. [Restaurant name]
            URL: [Restaurant URL]
            Description: [Restaurant description in plain text]
            5. [Restaurant name]
            URL: [Restaurant URL]
            Description: [Restaurant description in plain text]

            If no recommendation is appropriate, indicate that.
            '''),
            ("human", '''
            User question: {question}
            SQL query: {sql_query}
            Query results: {results}

            Recommend a recommendation:'''),
        ])

        response = self.llm_manager.invoke(prompt, question=question, sql_query=sql_query, results=results)

        # Parse the response to extract the recommendation
        lines = response.split('\n')
        
        recommendation = lines[0].split(': ')[1]
        reason = lines[1].split(': ')[1]

        # Format the recommendation data
        formatted_data = {
            "Top 5 Restaurants": [
                {"Restaurant name": "Example Restaurant 1", "URL": "http://example.com/1", "Description": "Great food."},
                {"Restaurant name": "Example Restaurant 2", "URL": "http://example.com/2", "Description": "Cozy ambiance."},
                {"Restaurant name": "Example Restaurant 3", "URL": "http://example.com/3", "Description": "Affordable prices."},
                {"Restaurant name": "Example Restaurant 4", "URL": "http://example.com/4", "Description": "Fantastic service."},
                {"Restaurant name": "Example Restaurant 5", "URL": "http://example.com/5", "Description": "Excellent reviews."}
            ]
        }

        return {
            "recommendation": recommendation,
            "recommendation_reason": reason,
            "formatted_data_for_recommendation": formatted_data  # Correctly return the dictionary
                }
