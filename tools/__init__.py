from .applescript_tool import applescript_tool
from .fazm_tool import fazm_tool
from .mac_control_tool import mac_control_tool
from .memory_tool import read_memory_tool, write_memory_tool


def create_all_tools(memory_path: str = "SNOWBALL.md") -> list:
    """创建所有自定义工具"""
    return [
        applescript_tool,
        fazm_tool,
        mac_control_tool,
        read_memory_tool,
        write_memory_tool,
    ]
