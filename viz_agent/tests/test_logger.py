# tests/test_logger.py

import pytest
import json
from pathlib import Path
from viz_agent.logger import VizAgentLogger
import tempfile
import shutil


@pytest.fixture
def temp_log_dir():
    """Crea directorio temporal para logs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_logger_initialization(temp_log_dir):
    """Test inicialización del logger"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    
    assert logger.log_dir == Path(temp_log_dir)
    assert logger.log_dir.exists()


def test_log_request(temp_log_dir):
    """Test logging de request"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_request("gráfico de barras", (100, 5))
    
    # Verificar que se creó el archivo de log
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    assert len(log_files) > 0


def test_log_decision(temp_log_dir):
    """Test logging de decisión"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_decision("bar", "Best for categorical data")
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    assert len(log_files) > 0


def test_log_validation_result_success(temp_log_dir):
    """Test logging de validación exitosa"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_validation_result(True)
    
    # Verificar contenido del log
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "SUCCESS" in content


def test_log_validation_result_failure(temp_log_dir):
    """Test logging de validación fallida"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_validation_result(False, "Syntax error")
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "FAILED" in content
        assert "Syntax error" in content


def test_log_correction_attempt(temp_log_dir):
    """Test logging de intento de corrección"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_correction_attempt(2, "runtime")
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "Attempt 2/5" in content
        assert "runtime" in content


def test_log_final_result_success(temp_log_dir):
    """Test logging de resultado final exitoso"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_final_result(True, 3, 2.5)
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "SUCCESS" in content
        assert "Attempts: 3" in content


def test_log_final_result_failure(temp_log_dir):
    """Test logging de resultado final fallido"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_final_result(False, 5, 10.0)
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "FAILED" in content


def test_log_error(temp_log_dir):
    """Test logging de error"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    logger.log_error("Something went wrong")
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "ERROR" in content
        assert "Something went wrong" in content


def test_create_session_log(temp_log_dir):
    """Test creación de session log en JSON"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    
    session_data = {
        "user_request": "gráfico de barras",
        "chart_type": "bar",
        "attempts": 2,
        "execution_time": 1.5
    }
    
    session_file = logger.create_session_log(session_data)
    
    # Verificar que se creó el archivo
    assert Path(session_file).exists()
    assert session_file.startswith(temp_log_dir)
    assert "session_" in session_file
    
    # Verificar contenido JSON
    with open(session_file, 'r') as f:
        loaded_data = json.load(f)
        assert loaded_data["user_request"] == "gráfico de barras"
        assert loaded_data["chart_type"] == "bar"
        assert loaded_data["attempts"] == 2


def test_multiple_log_calls(temp_log_dir):
    """Test múltiples llamadas de logging"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    
    logger.log_request("test", (10, 2))
    logger.log_decision("bar", "reason")
    logger.log_validation_result(True)
    logger.log_final_result(True, 1, 1.0)
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    assert len(log_files) == 1
    
    # Verificar que todos los logs están en el archivo
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "NEW REQUEST" in content
        assert "DECISION" in content
        assert "VALIDATION" in content
        assert "FINAL RESULT" in content


def test_log_code_generated(temp_log_dir):
    """Test logging de código generado"""
    logger = VizAgentLogger(log_dir=temp_log_dir)
    code = "import plotly.express as px\nfig = px.bar(df, x='a', y='b')"
    logger.log_code_generated(code)
    
    log_files = list(Path(temp_log_dir).glob("viz_agent_*.log"))
    with open(log_files[0], 'r') as f:
        content = f.read()
        assert "CODE GENERATED" in content
        assert "px.bar" in content
