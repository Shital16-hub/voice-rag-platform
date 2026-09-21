from app.core.logger import get_logger

logger = get_logger(__name__)


def lookup_leave_balance(employee_id: str, **kwargs) -> dict:
    logger.info(f"Tool: lookup_leave_balance employee_id={employee_id}")
    return {
        "employee_id": employee_id,
        "annual_leave_remaining": 15,
        "sick_leave_remaining": 8,
        "carried_forward": 2,
        "status": "success"
    }


def submit_leave_request(
    employee_id: str,
    start_date: str,
    end_date: str,
    days: int,
    reason: str = "",
    **kwargs
) -> dict:
    logger.info(f"Tool: submit_leave_request employee_id={employee_id} days={days}")
    return {
        "request_id": "LR-2024-001",
        "employee_id": employee_id,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "status": "pending_approval"
    }


def create_support_ticket(
    subject: str,
    description: str,
    priority: str = "medium",
    **kwargs
) -> dict:
    logger.info(f"Tool: create_support_ticket subject={subject}")
    return {
        "ticket_id": "TK-2024-001",
        "subject": subject,
        "priority": priority,
        "status": "open",
        "created_at": "2024-01-15T10:30:00"
    }


def get_ticket_status(ticket_id: str, **kwargs) -> dict:
    logger.info(f"Tool: get_ticket_status ticket_id={ticket_id}")
    return {
        "ticket_id": ticket_id,
        "status": "in_progress",
        "assigned_to": "Support Team",
        "last_updated": "2024-01-15T14:00:00"
    }


def create_sales_lead(
    name: str,
    email: str,
    company: str,
    interest: str = "",
    **kwargs
) -> dict:
    logger.info(f"Tool: create_sales_lead name={name}")
    return {
        "lead_id": "LD-2024-001",
        "name": name,
        "email": email,
        "company": company,
        "status": "new"
    }


def schedule_callback(
    name: str,
    phone: str,
    preferred_time: str,
    **kwargs
) -> dict:
    logger.info(f"Tool: schedule_callback name={name}")
    return {
        "callback_id": "CB-2024-001",
        "name": name,
        "phone": phone,
        "preferred_time": preferred_time,
        "status": "scheduled"
    }


TOOL_REGISTRY = {
    "lookup_leave_balance": {
        "function": lookup_leave_balance,
        "description": "Check employee leave balance",
        "requires_approval": False,
        "parameters": {
            "employee_id": "string - the employee ID"
        }
    },
    "submit_leave_request": {
        "function": submit_leave_request,
        "description": "Submit a leave request for an employee",
        "requires_approval": True,
        "parameters": {
            "employee_id": "string - the employee ID",
            "start_date": "string - start date YYYY-MM-DD",
            "end_date": "string - end date YYYY-MM-DD",
            "days": "integer - number of days",
            "reason": "string - reason for leave"
        }
    },
    "create_support_ticket": {
        "function": create_support_ticket,
        "description": "Create a new support ticket",
        "requires_approval": True,
        "parameters": {
            "subject": "string - ticket subject",
            "description": "string - detailed description",
            "priority": "string - low/medium/high"
        }
    },
    "get_ticket_status": {
        "function": get_ticket_status,
        "description": "Check status of a support ticket",
        "requires_approval": False,
        "parameters": {
            "ticket_id": "string - the ticket ID"
        }
    },
    "create_sales_lead": {
        "function": create_sales_lead,
        "description": "Create a new sales lead",
        "requires_approval": False,
        "parameters": {
            "name": "string - lead name",
            "email": "string - lead email",
            "company": "string - company name",
            "interest": "string - area of interest"
        }
    },
    "schedule_callback": {
        "function": schedule_callback,
        "description": "Schedule a callback for a customer",
        "requires_approval": False,
        "parameters": {
            "name": "string - customer name",
            "phone": "string - phone number",
            "preferred_time": "string - preferred callback time"
        }
    }
}


def get_available_tools(tools_enabled: list[str]) -> dict:
    available = {}
    for tool_name in tools_enabled:
        if tool_name in TOOL_REGISTRY:
            available[tool_name] = TOOL_REGISTRY[tool_name]
        else:
            logger.warning(f"Unknown tool requested tool={tool_name}")
    return available


def execute_builtin_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Tool not found: {tool_name}")
    tool_fn = TOOL_REGISTRY[tool_name]["function"]
    return tool_fn(**tool_input)


def tool_requires_approval(tool_name: str) -> bool:
    if tool_name not in TOOL_REGISTRY:
        return False
    return TOOL_REGISTRY[tool_name].get("requires_approval", False)