from .applescript_tool import create_applescript_tool
from .fazm_tool import create_fazm_tool
from .mac_control_tool import create_mac_control_tool
from .memory_tool import create_read_memory_tool, create_write_memory_tool


def create_all_tools(memory_path: str = "SNOWBALL.md") -> list:
    """创建所有自定义工具"""
    return [
        create_applescript_tool(),
        create_fazm_tool(),
        create_mac_control_tool(),
        create_read_memory_tool(memory_path),
        create_write_memory_tool(memory_path),
    ]
