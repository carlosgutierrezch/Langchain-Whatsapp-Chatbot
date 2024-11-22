from WorkflowManager import Workflow
from SQLAgent import SQLAgent

agent= SQLAgent()
agent_executor= Workflow()
query='what is the best restaurant by rating'
print(agent.db_manager.get_schema())
name='carlos'
response = agent_executor.run_sql_agent(query,name)
print(response)