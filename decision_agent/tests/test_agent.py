import pytest
import uuid
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from decision_agent.agent import DecisionAgent
from decision_agent.models import (
    DecisionAgentInput, 
    IntentCategory, 
    IntentClassification, 
    ResponseType
)
from decision_agent.exceptions import PipelineError, SQLValidationError

@pytest.fixture
def mock_vanna_agent():
    mock = MagicMock()
    mock.text_to_sql = AsyncMock()
    mock.execute_sql = AsyncMock()
    return mock

@pytest.fixture
def mock_viz_agent():
    mock = MagicMock()
    mock.generate_visualization = AsyncMock()
    return mock

@pytest.fixture
def agent(mock_vanna_agent, mock_viz_agent):
    with patch("decision_agent.agent.IntentClassifier") as mock_cls:
        with patch("decision_agent.agent.SQLValidator") as mock_val:
            agent_inst = DecisionAgent(
                text2sql_agent=mock_vanna_agent,
                viz_agent=mock_viz_agent
            )
            # Make the classifier's classify method an AsyncMock
            agent_inst.classifier.classify = AsyncMock()
            agent_inst.sql_validator = mock_val.return_value
            yield agent_inst

@pytest.mark.asyncio
async def test_run_visualization_success(agent, mock_vanna_agent, mock_viz_agent):
    # Mock classifier
    agent.classifier.classify.return_value = IntentClassification(
        category=IntentCategory.VALID_AND_CLEAR,
        reasoning="Query is clear"
    )
    
    # Mock Vanna (Text2SQL)
    mock_vanna_agent.text_to_sql.return_value = MagicMock(success=True, sql="SELECT * FROM sales")
    mock_vanna_agent.execute_sql.return_value = pd.DataFrame({"a": [1, 2]})
    
    # Mock Viz
    mock_viz_agent.generate_visualization.return_value = MagicMock(success=True, plotly_json={"data": []})
    
    input_data = DecisionAgentInput(query="show sales", session_id=uuid.uuid4())
    output = await agent.run(input_data)
    
    assert output.response_type == ResponseType.VISUALIZATION
    assert output.sql == "SELECT * FROM sales"
    assert output.viz_result is not None
    assert agent.classifier.classify.called

@pytest.mark.asyncio
async def test_run_clarification(agent):
    agent.classifier.classify.return_value = IntentClassification(
        category=IntentCategory.VALID_BUT_AMBIGUOUS,
        reasoning="Ambiguous query",
        clarification_question="What do you mean?"
    )
    
    input_data = DecisionAgentInput(query="sales", session_id=uuid.uuid4())
    output = await agent.run(input_data)
    
    assert output.response_type == ResponseType.CLARIFICATION
    assert "What do you mean?" in output.message

@pytest.mark.asyncio
async def test_run_retry_on_sql_error(agent, mock_vanna_agent, mock_viz_agent):
    agent.classifier.classify.return_value = IntentClassification(
        category=IntentCategory.VALID_AND_CLEAR,
        reasoning="Clear query"
    )
    
    # First attempt fails, second succeeds
    mock_vanna_agent.text_to_sql.side_effect = [
        MagicMock(success=True, sql="SELECT bad FROM table"),
        MagicMock(success=True, sql="SELECT good FROM table")
    ]
    mock_vanna_agent.execute_sql.side_effect = [
        Exception("Column bad not found"),
        pd.DataFrame({"good": [100]})
    ]
    
    mock_viz_agent.generate_visualization.return_value = MagicMock(success=True, plotly_json={})
    
    input_data = DecisionAgentInput(query="show good sales", session_id=uuid.uuid4())
    output = await agent.run(input_data)
    
    assert output.response_type == ResponseType.VISUALIZATION
    assert output.sql == "SELECT good FROM table"
    assert output.metadata["attempts"] == 2

@pytest.mark.asyncio
async def test_run_timeout(agent):
    async def slow_classify(*args, **kwargs):
        await asyncio.sleep(2)
        return IntentClassification(category=IntentCategory.VALID_AND_CLEAR, reasoning="Clear query")
        
    agent.classifier.classify.side_effect = slow_classify
    
    # Patch the timeout value locally for this test so we don't wait 30 seconds
    agent.settings.PIPELINE_TIMEOUT_SECONDS = 0.1
    
    input_data = DecisionAgentInput(query="test timeout", session_id=uuid.uuid4())
    with pytest.raises(PipelineError) as exc_info:
        await agent.run(input_data)
        
    assert "timeout" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_sql_validation_error_no_retry(agent, mock_vanna_agent):
    agent.classifier.classify.return_value = IntentClassification(
        category=IntentCategory.VALID_AND_CLEAR,
        reasoning="Clear query"
    )
    mock_vanna_agent.text_to_sql.return_value = MagicMock(success=True, sql="DELETE FROM users")
    agent.sql_validator.validate.side_effect = SQLValidationError("Only SELECT allowed")
    
    input_data = DecisionAgentInput(query="delete users", session_id=uuid.uuid4())
    
    with pytest.raises(SQLValidationError):
        await agent.run(input_data)
    
    # Should not retry on SQLValidationError according to our logic
    assert mock_vanna_agent.execute_sql.call_count == 0
