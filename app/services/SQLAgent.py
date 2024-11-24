from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
<<<<<<< HEAD
from DatabaseManager import DatabaseManager
from LLMManager import LLMManager
=======
from app.services.DatabaseManager import DatabaseManager
from app.services.LLMManager import LLMManager
>>>>>>> 69a94044205ec7ebdabb3d49af6431e7c830a426


class SQLAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_manager = LLMManager()

    def parse_question(self, state: dict) -> dict:
        """Parse user question and identify relevant tables and columns."""
        question = state['question']
        schema = self.db_manager.get_schema()
        print(f"Schema fetched: {schema}")  # Debugging line
        prompt = ChatPromptTemplate.from_messages([
            ("system", '''You are a data analyst that can help summarize SQL tables and parse user questions about a database. 
            Given the question and database schema, identify the relevant tables and columns. 
            If the question is not relevant to the database or if there is not enough information to answer the question, set is_relevant to false.

            Your response should be in the following JSON format:
            {{
                "is_relevant": boolean,
                "relevant_tables": [
                    {{
                        "table_name": string,
                        "columns": [string],
                        "noun_columns": [string]
                    }}
                ]
            }}

            The "noun_columns" field should contain only the columns that are relevant to the question and contain nouns or names, for example, the column "Artist name" contains nouns relevant to the question "What are the top selling artists?", but the column "Artist ID" is not relevant because it does not contain a noun. Do not include columns that contain numbers.
            '''),
            ("human", "===Database schema:\n{schema}\n\n===User question:\n{question}\n\nIdentify relevant tables and columns:")
        ])

        output_parser = JsonOutputParser()
        response = self.llm_manager.invoke(prompt, schema=schema, question=question)
        parsed_response = output_parser.parse(response)
        return {"parsed_question": parsed_response}

    def get_unique_nouns(self, state: dict) -> dict:
        """Find unique nouns in relevant tables and columns."""
        parsed_question = state['parsed_question']
        
        if not parsed_question['is_relevant']:
            return {"unique_nouns": []}

        unique_nouns = set()
        for table_info in parsed_question['relevant_tables']:
            table_name = table_info['table_name']
            noun_columns = table_info['noun_columns']
            
            if noun_columns:
                column_names = ', '.join(f"`{col}`" for col in noun_columns)
                query = f"SELECT DISTINCT {column_names} FROM `{table_name}`"
                results = self.db_manager.execute_query(query)
                for row in results:
                    unique_nouns.update(str(value) for value in row if value)

        return {"unique_nouns": list(unique_nouns)}

    def generate_sql(self, state: dict) -> dict:
        """Generate SQL query based on parsed question and unique nouns."""
        question = state['question']
        parsed_question = state['parsed_question']
        unique_nouns = state['unique_nouns']

        if not parsed_question['is_relevant']:
            return {"sql_query": "NOT_RELEVANT", "is_relevant": False}
    
        schema = self.db_manager.get_schema()
        print(f"Schema fetched: {schema}")  # Debugging line
        prompt = ChatPromptTemplate.from_messages([
            ("system", '''
            You are an AI assistant that generates SQL queries based on user questions, database schema, and unique nouns found in the relevant tables. Generate a valid SQL query to answer the user's question.

            If there is not enough information to write a SQL query, respond with "NOT_ENOUGH_INFO".

            Here are some examples:

            1. What is the best restaurant?
            Answer: SELECT name, rating, url FROM data_restaurants ORDER BY rating DESC LIMIT 5

            2. What is the restaurant with the worst rating in madrid?
            Answer: SELECT name, rating, url FROM data_restaurants ORDER BY rating ASC LIMIT 5
            
            3. What is the price range in the best restaurant?
            Answer: SELECT name AS best_restaurant, 
                    rating AS highest_rating, 
                    price_range
                    FROM restaurants
                    WHERE rating = (SELECT MAX(rating) FROM restaurants);
            

            SKIP ALL ROWS WHERE ANY COLUMN IS NULL or "N/A" or "".
            Just give the query string. Do not format it. Make sure to use the correct spellings of nouns as provided in the unique nouns list. All the table and column names should be enclosed in backticks.
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
        
        schema = self.db_manager.get_schema()
        print(f"Schema fetched: {schema}")  # Debugging line

        # Ensure that schema and sql_query are properly passed in the format
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

            For example:
            1. {{
                "valid": true,
                "issues": null,
                "corrected_query": "None"
            }}
                                        
            2. {{
                "valid": false,
                "issues": "Column USERS does not exist",
                "corrected_query": "SELECT * FROM \\`users\\` WHERE age > 25"
            }}

            3. {{
                "valid": false,
                "issues": "Column names and table names should be enclosed in backticks if they contain spaces or special characters",
                "corrected_query": "SELECT * FROM \\`gross income\\` WHERE \\`age\\` > 25"
            }}
            '''),
        ])

        output_parser = JsonOutputParser()

        # Ensure that you're passing both schema and sql_query properly as keyword arguments
        response = self.llm_manager.invoke(prompt, schema=schema, sql_query=sql_query)
        
        # Parsing the response from the language model
        result = output_parser.parse(response)

        # Check the validation result and return accordingly
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
        # uuid = state['uuid']
        
        if query == "NOT_RELEVANT":
            return {"results": "NOT_RELEVANT"}

        try:
            results = self.db_manager.execute_query(query)
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    def format_results(self, state: dict) -> dict:
        """Format query results into a human-readable response."""
        question = state['question']
        results = state['results']

        if results == "NOT_RELEVANT":
            return {"answer": "Sorry, I can only give answers relevant to the database."}

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
            return {"recommendation": "none", "recommendation_reasoning": "No recommendation needed for irrelevant questions."}

        prompt = ChatPromptTemplate.from_messages([
            ("system", '''
             You are an AI assistant that specializes in recommending restaurants. Based on the user's question, the SQL query, and the query results, provide the most accurate and suitable restaurant recommendation. If no recommendation fits, clearly state that no suitable option is available.

            When making recommendations, consider these factors:
            - Location: Prioritize restaurants near the specified area or region.
            - Cuisine: Match the cuisine type or style the user is asking for (e.g., "Italian," "Vegan").
            - Ratings: Favor restaurants with higher ratings or reviews if applicable.
            - Price Range: Consider the price range based on the user's preferences or question.
            - Special Requests: Address specific requirements like "family-friendly," "romantic atmosphere," or dietary preferences like "gluten-free."
            
            Provide concise and actionable recommendations. Use the query results to support your answers when appropriate. Do NOT recommend a restaurant if the available data does not support it.

            Output your response in the following format:
            Recommended restaurant: [Name of the restaurant or "None" if no recommendation is suitable]
            Reason: [Explain why this restaurant was chosen based on location, cuisine, rating, etc.]
            Additional information: [Optional details like opening hours, special offers, or unique features]
            '''),
            
            ("human", '''
            User question: {question}
            SQL query: {sql_query}
            Query results: {results}

            Recommend a restaurant:'''),
                    ])

        response = self.llm_manager.invoke(prompt, question=question, sql_query=sql_query, results=results)
        
        lines = response.split('\n')
        recommendation = lines[0].split(': ')[1]
        reason = lines[1].split(': ')[1]

        return {"recommendation": recommendation, "recommendation_reason": reason}
<<<<<<< HEAD




# class SQLAgent:
#     def __init__(self):
#         self.db_manager = DatabaseManager()
#         self.llm_manager = LLMManager()

#     def parse_question(self, state: dict) -> dict:
#         """Parse user question and identify relevant tables and columns."""
#         question = state['question']
#         schema = self.db_manager.get_schema()
#         print(f"Schema fetched: {schema}")  # Debugging line
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", '''You are a data analyst that can help summarize SQL tables and parse user questions 
#             about a database. Given the question and database schema, identify the relevant tables and columns.
            
#             If the question is not relevant to the database or if there is not enough information to answer the question, set is_relevant to false.

#             Your response should be in the following JSON format:
#             {{
#                 "is_relevant": boolean,
#                 "relevant_tables": [
#                     {{
#                         "table_name": string,
#                         "columns": [string],
#                         "noun_columns": [string]
#                     }}
#                 ]
#             }}

#             The "noun_columns" field should contain only the columns that are relevant to the question and contain nouns or names, for example, the column "reviews" contains nouns relevant to the question "What are the top restaurants?", but the column "place_id" is not relevant because it does not contain a noun. Do not include columns that contain numbers.
#             '''),
#             ("human", "===Database schema:\n{schema}\n\n===User question:\n{question}\n\nIdentify relevant tables and columns:")
#         ])
#         print(prompt)
#         output_parser = JsonOutputParser()
#         response = self.llm_manager.invoke(prompt, schema=schema, question=question)
#         print(response)
#         parsed_response = output_parser.parse(response)
#         print(parsed_response)
#         return {"parsed_question": parsed_response}

#     def get_unique_nouns(self, state: dict) -> dict:
#         """Find unique nouns in relevant tables and columns."""
#         parsed_question = state['parsed_question']
        
#         if not parsed_question['is_relevant']:
#             return {"unique_nouns": []}

#         unique_nouns = set()
#         for table_info in parsed_question['relevant_tables']:
#             table_name = table_info['table_name']
#             noun_columns = table_info['noun_columns']
            
#             if noun_columns:
#                 column_names = ', '.join(f"`{col}`" for col in noun_columns)
#                 query = f"SELECT DISTINCT {column_names} FROM `{table_name}`"
#                 results = self.db_manager.execute_query(query)
#                 for row in results:
#                     unique_nouns.update(str(value) for value in row if value)
#         print(unique_nouns)
#         return {"unique_nouns": list(unique_nouns)}

#     def generate_sql(self, state: dict) -> dict:
#         """Generate SQL query based on parsed question and unique nouns.
#             There is a massive problem with this approach, the think is that if we just use this process we are going to call me same restaurant over and over
#             The chain needs more data (dynamic subjective data) to create a metric where the llm can grab mor information and retrieve an accurate recommendation
#             Double-check the reasoning to see what were the steps taken to make the recommendation"""
#         question = state['question']
#         parsed_question = state['parsed_question']
#         unique_nouns = state['unique_nouns']

#         if not parsed_question['is_relevant']:
#             return {"sql_query": "NOT_RELEVANT", "is_relevant": False} # cambiar esta condicional aqui

#         schema = self.db_manager.get_schema()
#         print(f"Schema fetched: {schema}")  # Debugging line
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", '''
#             You are an AI assistant that generates SQL queries based on user questions, database schema, and unique nouns found in the relevant tables. Generate a valid SQL query to answer the user's question.

#             If there is not enough information to write a SQL query, respond with "NOT_ENOUGH_INFO".

#             Here are some examples:

#             1. What is the best restaurant?
#             Answer: SELECT name, rating, url FROM data_restaurants ORDER BY rating DESC LIMIT 5

#             2. What is the restaurant with the worst rating in madrid?
#             Answer: SELECT name, rating, url FROM data_restaurants ORDER BY rating ASC LIMIT 5
            
#             3. What is the price range in the best restaurant?
#             Answer: SELECT name AS best_restaurant, 
#                     rating AS highest_rating, 
#                     price_range
#                     FROM restaurants
#                     WHERE rating = (SELECT MAX(rating) FROM restaurants);
            

#             SKIP ALL ROWS WHERE ANY COLUMN IS NULL or "N/A" or "".
#             Just give the query string. Do not format it. Make sure to use the correct spellings of nouns as provided in the unique nouns list. All the table and column names should be enclosed in backticks.
#             '''),
#                         ("human", '''===Database schema:
#             {schema}

#             ===User question:
#             {question}

#             ===Relevant tables and columns:
#             {parsed_question}

#             ===Unique nouns in relevant tables:
#             {unique_nouns}

#             Generate SQL query string'''),
#         ])

#         response = self.llm_manager.invoke(prompt, schema=schema, question=question, parsed_question=parsed_question, unique_nouns=unique_nouns)
        
#         if response.strip() == "NOT_ENOUGH_INFO":
#             return {"sql_query": "NOT_RELEVANT"}
#         else:
#             print(response)
#             return {"sql_query": response}


#     def validate_and_fix_sql(self, state: dict) -> dict:
#         """Validate and fix the generated SQL query."""
#         sql_query = state['sql_query']

#         if sql_query == "NOT_RELEVANT":
#             return {"sql_query": "NOT_RELEVANT", "sql_valid": False}
        
#         schema = self.db_manager.get_schema()
#         print(f"Schema fetched: {schema}")  # Debugging line

#         # Ensure that schema and sql_query are properly passed in the format
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", '''
#             You are an AI assistant that validates and fixes SQL queries. Your task is to:
#             1. Check if the SQL query is valid.
#             2. Ensure all table and column names are correctly spelled and exist in the schema. All the table and column names should be enclosed in backticks.
#             3. If there are any issues, fix them and provide the corrected SQL query.
#             4. If no issues are found, return the original query.

#             Respond in JSON format with the following structure. Only respond with the JSON:
#             {{
#                 "valid": boolean,
#                 "issues": string or null,
#                 "corrected_query": string
#             }}
#             '''),
#             ("human", '''===Database schema:
#             {schema}

#             ===Generated SQL query:
#             {sql_query}

#             Respond in JSON format with the following structure. Only respond with the JSON:
#             {{
#                 "valid": boolean,
#                 "issues": string or null,
#                 "corrected_query": string
#             }}

#             For example:
#             1. {{
#                 "valid": true,
#                 "issues": null,
#                 "corrected_query": "None"
#             }}
                                        
#             2. {{
#                 "valid": false,
#                 "issues": "Column USERS does not exist",
#                 "corrected_query": "SELECT * FROM \\`users\\` WHERE age > 25"
#             }}

#             3. {{
#                 "valid": false,
#                 "issues": "Column names and table names should be enclosed in backticks if they contain spaces or special characters",
#                 "corrected_query": "SELECT * FROM \\`gross income\\` WHERE \\`age\\` > 25"
#             }}
#             '''),
#         ])

#         output_parser = JsonOutputParser()

#         # Ensure that you're passing both schema and sql_query properly as keyword arguments
#         response = self.llm_manager.invoke(prompt, schema=schema, sql_query=sql_query)
#         print(response)
#         # Parsing the response from the language model
#         result = output_parser.parse(response)

#         # Check the validation result and return accordingly
#         if result["valid"] and result["issues"] is None:
#             return {"sql_query": sql_query, "sql_valid": True}
#         else:
#             return {
#                 "sql_query": result["corrected_query"],
#                 "sql_valid": result["valid"],
#                 "sql_issues": result["issues"]
#             }
        
#     def execute_sql(self, state: dict) -> dict:
#         """Execute SQL query and return results."""
#         query = state['sql_query']
#         # uuid = state['uuid']
        
#         if query == "NOT_RELEVANT":
#             return {"results": "NOT_RELEVANT"}

#         try:
#             results = self.db_manager.execute_query(query)
#             print(results)
#             return {"results": results}
#         except Exception as e:
#             return {"error": str(e)}

#     def format_results(self, state: dict) -> dict:
#         """Format query results into a human-readable response."""
#         question = state['question']
#         results = state['results']

#         if results == "NOT_RELEVANT":
#             return {"answer": "Sorry, I can only give answers relevant to the database."}

#         prompt = ChatPromptTemplate.from_messages([
#             ("system", "You are an AI assistant that formats database query results into a human-readable response. Give a conclusion to the user's question based on the query results. Do not give the answer in markdown format. Only give the answer in one line."),
#             ("human", "User question: {question}\n\nQuery results: {results}\n\nFormatted response:"),
#         ])

#         response = self.llm_manager.invoke(prompt, question=question, results=results)
#         print(response)
#         return {"answer": response}

#     def choose_recommendation(self, state: dict) -> dict:
#         """Choose an appropriate recommendation from the data."""
#         question = state['question']
#         results = state['results']
#         sql_query = state['sql_query']

#         if results == "NOT_RELEVANT":
#             return {"recommendation": "none", "recommendation_reasoning": "No recommendation needed for irrelevant questions."}

#         prompt = ChatPromptTemplate.from_messages([
#             ("system", '''
#                 You are an AI assistant that specializes in recommending restaurants. Based on the user's question, the SQL query, and the query results, provide the most accurate and suitable restaurant recommendation. If no recommendation fits, clearly state that no suitable option is available.

#             When making recommendations, consider these factors:
#             - Location: Prioritize restaurants near the specified area or region.
#             - Cuisine: Match the cuisine type or style the user is asking for (e.g., "Italian," "Vegan").
#             - Ratings: Favor restaurants with higher ratings or reviews if applicable.
#             - Price Range: Consider the price range based on the user's preferences or question.
#             - Special Requests: Address specific requirements like "family-friendly," "romantic atmosphere," or dietary preferences like "gluten-free."
            
#             Provide concise and actionable recommendations. Use the query results to support your answers when appropriate. Do NOT recommend a restaurant if the available data does not support it.

#             Output your response in the following format:
#             Recommended restaurant: [Name of the restaurant or "None" if no recommendation is suitable]
#             Reason: [Explain why this restaurant was chosen based on location, cuisine, rating, etc.]
#             Additional information: [Optional details like opening hours, special offers, or unique features]
#             '''),
            
#             ("human", '''
#             User question: {question}
#             SQL query: {sql_query}
#             Query results: {results}

#             Recommend a restaurant:'''),
#                     ])

#         response = self.llm_manager.invoke(prompt, question=question, sql_query=sql_query, results=results)
        
#         lines = response.split('\n')
#         recommendation = lines[0].split(': ')[1]
#         reason = lines[1].split(': ')[1]

#         return {"recommendation": recommendation, "recommendation_reason": reason}
=======
>>>>>>> 69a94044205ec7ebdabb3d49af6431e7c830a426
