from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.services.DatabaseManager import DatabaseManager
from app.services.LLMManager import LLMManager



class SQLAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm_manager = LLMManager()

    def parse_question(self, state: dict) -> dict:
        """Parse user question and identify relevant tables and columns."""
        question = state['question']
        schema = self.db_manager.get_schema()

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
                results = self.db_manager.execute_query(state['uuid'], query)
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
                "corrected_query": "SELECT * FROM \`users\` WHERE age > 25"
            }}

            3. {{
                "valid": false,
                "issues": "Column names and table names should be enclosed in backticks if they contain spaces or special characters",
                "corrected_query": "SELECT * FROM \`gross income\` WHERE \`age\` > 25"
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

# class RestaurantAgent:
#     def __init__(self):
#         self.db_manager = DatabaseManager()
#         self.llm_manager = LLMManager()
    
#     def is_greeting(self, text: str) -> bool:
#         """Detect if the message is a greeting in either English or Spanish."""
#         greetings = {
#             'en': r'\b(hi|hello|hey|good morning|good afternoon|good evening|sup|what\'s up)\b',
#             'es': r'\b(hola|buenos días|buenas tardes|buenas noches|qué tal|que tal)\b'
#         }
#         combined_pattern = '|'.join(greetings.values())
#         return bool(re.search(combined_pattern, dict(text)))
    
#     def detect_language(self, text: str) -> str:
#         """Detect if the message is in English or Spanish."""
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", "You are a language detector. Respond only with 'en' for English or 'es' for Spanish."),
#             ("human", "{text}")
#         ])
#         return self.llm_manager.invoke(prompt, text=text).strip().lower()
    
#     def is_restaurant_query(self, text: str) -> bool:
#         """Detect if the message is a restaurant-related query."""
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """Determine if the message is asking about restaurants, food, dining, or related topics.
#             Respond only with 'true' or 'false'."""),
#             ("human", "{text}")
#         ])
#         response = self.llm_manager.invoke(prompt, text=text).strip().lower()
#         return response == 'true'

#     def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
#         """Main entry point for processing user messages."""
#         # Detect language
#         language = self.detect_language(message)
        
#         # If it's a greeting, respond casually
#         if self.is_greeting(message):
#             return self.get_casual_response(message, language)
            
#         # If it's not a restaurant query, maintain casual conversation
#         if not self.is_restaurant_query(message):
#             return self.get_casual_response(message, language)
            
#         # If it is a restaurant query, process it
#         return self.process_restaurant_query(message, language, user_id)

#     def get_casual_response(self, text: str, language: str) -> Dict[str, Any]:
#         """Generate a casual, context-aware response."""
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """You are a friendly WhatsApp chatbot that helps people find restaurants in Madrid. 
#             Keep responses casual and brief (1-2 sentences max). If user writes in Spanish, respond in Spanish.
#             If they write in English, respond in English. Maintain a warm, helpful tone."""),
#             ("human", "{text}")
#         ])
        
#         response = self.llm_manager.invoke(prompt, text=text)
        
#         return {
#             "answer": response,
#             "recommendation": None,
#             "urls": []
#         }

#     def process_restaurant_query(self, question: str, language: str, user_id: str) -> Dict[str, Any]:
#         """Process a restaurant-related query and generate recommendations."""
#         # Get schema and generate query
#         schema = self.db_manager.get_schema(user_id)
        
#         # Generate and execute SQL query
#         sql_result = self.generate_and_execute_sql(question, schema, user_id)
        
#         if not sql_result.get("results"):
#             return self.get_no_results_response(language)
            
#         # Format recommendation
#         return self.format_recommendation(
#             question=question,
#             results=sql_result["results"],
#             language=language
#         )

#     def generate_and_execute_sql(self, question: str, schema: str, user_id: str) -> Dict[str, Any]:
#         """Generate and execute SQL query."""
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """Generate a SQL query to find restaurants based on the user's question.
#             Ensure proper table/column names and handle nulls."""),
#             ("human", """Schema: {schema}
#             Question: {question}
#             Generate SQL:""")
#         ])
        
#         sql_query = self.llm_manager.invoke(prompt, schema=schema, question=question)
        
#         try:
#             results = self.db_manager.execute_query(user_id, sql_query)
#             return {"results": results}
#         except Exception as e:
#             return {"error": str(e)}

#     def format_recommendation(self, question: str, results: list, language: str) -> Dict[str, Any]:
#         """Format the restaurant recommendations in the user's language."""
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """You are a friendly WhatsApp restaurant recommender for Madrid.
#             Format the response in the user's language (Spanish/English).
#             Keep it casual and brief.
#             Include restaurant names, brief descriptions, and URLs if available.
#             Limit to top 3 recommendations.
#             Make it easy to read on a mobile device."""),
#             ("human", """Question: {question}
#             Results: {results}
#             Language: {language}
#             Format response:""")
#         ])
        
#         response = self.llm_manager.invoke(
#             prompt,
#             question=question,
#             results=results,
#             language=language
#         )
        
#         # Extract URLs from the response for WhatsApp clickable links
#         urls = self.extract_urls(response)
        
#         return {
#             "answer": response,
#             "urls": urls,
#             "recommendation": True
#         }

#     def get_no_results_response(self, language: str) -> Dict[str, Any]:
#         """Generate a response when no restaurants match the criteria."""
#         templates = {
#             'en': "I couldn't find any restaurants matching those criteria. Could you try being more specific or changing your preferences?",
#             'es': "No encontré restaurantes que coincidan con esos criterios. ¿Podrías ser más específico o cambiar tus preferencias?"
#         }
        
#         return {
#             "answer": templates.get(language, templates['en']),
#             "recommendation": None,
#             "urls": []
#         }

#     def extract_urls(self, text: str) -> list:
#         """Extract URLs from text for WhatsApp clickable links."""
#         url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
#         return re.findall(url_pattern, text)